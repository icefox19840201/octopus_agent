import uuid
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from settings import DATABASE_URL
from utils.logger import logger

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    # 迁移：为agents表添加config列（如果不存在）
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("agents")]
    if "config" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE agents ADD COLUMN config TEXT NULL COMMENT '智能体配置(JSON)'"))
            conn.commit()
            logger.info("数据库迁移: agents表已添加config列")
    _seed_initial_data()


def _seed_initial_data():
    from dataaccess.models import UserModel, RoleModel, PermissionModel, RolePermissionMapping, UserRoleMapping, DepartmentModel, PromptModel
    import hashlib
    db = SessionLocal()
    try:
        if db.query(UserModel).count() > 0:
            return

        # 创建默认部门
        dept_tech_id = "dept_tech"
        dept_product_id = "dept_product"
        dept_sales_id = "dept_sales"
        dept_hr_id = "dept_hr"

        db.add(DepartmentModel(
            id=dept_tech_id,
            name="技术部",
            code="TECH",
            description="负责产品研发和技术支持",
            sort_order=1,
            status="active"
        ))
        db.add(DepartmentModel(
            id=dept_product_id,
            name="产品部",
            code="PRODUCT",
            description="负责产品规划和设计",
            sort_order=2,
            status="active"
        ))
        db.add(DepartmentModel(
            id=dept_sales_id,
            name="销售部",
            code="SALES",
            description="负责市场拓展和销售",
            sort_order=3,
            status="active"
        ))
        db.add(DepartmentModel(
            id=dept_hr_id,
            name="人事部",
            code="HR",
            description="负责人力资源管理",
            sort_order=4,
            status="active"
        ))

        # 提交部门以获取ID
        db.flush()

        # 创建默认权限 - 菜单权限
        # 图标名称必须与 templates/default.html 中定义的 symbol id 匹配
        menu_permissions = [
            # (key, name, menu_path, menu_icon, menu_order)
            ("menu:dashboard", "仪表盘", "dashboard", "dashboard", 1),
            ("menu:agents", "Agent管理", "agents", "users", 2),
            ("menu:skills", "Skill管理", "skills", "cogs", 3),
            ("menu:mcp", "MCP管理", "mcp", "server", 4),
            ("menu:models", "模型管理", "models", "cpu", 6),
            ("menu:prompts", "提示词管理", "prompts", "circle", 5),
            ("menu:rag", "知识库管理", "rag", "puzzle", 7),
            ("menu:permission", "权限管控", "permission", "shield", 8),
        ]



        perm_id_map = {}
        idx = 1
        
        # 创建菜单权限 - 检查是否已存在
        for key, name, menu_path, menu_icon, menu_order in menu_permissions:
            # 检查权限是否已存在
            existing = db.query(PermissionModel).filter(PermissionModel.key == key).first()
            if existing:
                perm_id_map[key] = existing.id
                continue
            
            perm_id = f"perm_{idx:03d}"
            perm_id_map[key] = perm_id
            db.add(PermissionModel(
                id=perm_id,
                key=key,
                name=name,
                is_menu=True,
                menu_path=menu_path,
                menu_icon=menu_icon,
                menu_order=menu_order,
                status="active"
            ))
            idx += 1
        

        # 创建默认角色
        role_admin_id = "role_admin"
        role_editor_id = "role_editor"
        role_viewer_id = "role_viewer"

        db.add(RoleModel(
            id=role_admin_id,
            name="管理员",
            code="admin",
            description="系统管理员，拥有所有权限",
            status="active"
        ))
        db.add(RoleModel(
            id=role_editor_id,
            name="编辑者",
            code="editor",
            description="可管理智能体和技能",
            status="active"
        ))
        db.add(RoleModel(
            id=role_viewer_id,
            name="查看者",
            code="viewer",
            description="仅可查看",
            status="active"
        ))

        # 提交角色和权限以获取ID
        db.flush()

        # 管理员拥有所有权限
        for key, perm_id in perm_id_map.items():
            db.add(RolePermissionMapping(
                id=f"rpm_{uuid.uuid4().hex[:8]}",
                role_id=role_admin_id,
                permission_id=perm_id
            ))

        # 编辑者权限
        editor_perm_keys = [
            "agent:view", "agent:create", "agent:update", "agent:delete", "agent:chat",
            "skill:view", "skill:create", "skill:update", "skill:delete"
        ]
        for key in editor_perm_keys:
            if key in perm_id_map:
                db.add(RolePermissionMapping(
                    id=f"rpm_{uuid.uuid4().hex[:8]}",
                    role_id=role_editor_id,
                    permission_id=perm_id_map[key]
                ))

        # 查看者权限
        viewer_perm_keys = ["agent:view", "skill:view", "agent:chat"]
        for key in viewer_perm_keys:
            if key in perm_id_map:
                db.add(RolePermissionMapping(
                    id=f"rpm_{uuid.uuid4().hex[:8]}",
                    role_id=role_viewer_id,
                    permission_id=perm_id_map[key]
                ))

        # 创建默认用户（关联部门）
        admin_id = "user_admin"
        admin_password_hash = hashlib.sha256("admin123".encode('utf-8')).hexdigest()
        db.add(UserModel(
            id=admin_id,
            username="admin",
            email="admin@example.com",
            password_hash=admin_password_hash,
            real_name="系统管理员",
            department_id=dept_tech_id,
            status="active"
        ))

        editor_id = "user_editor"
        editor_password_hash = hashlib.sha256("editor123".encode('utf-8')).hexdigest()
        db.add(UserModel(
            id=editor_id,
            username="editor",
            email="editor@example.com",
            password_hash=editor_password_hash,
            real_name="编辑用户",
            department_id=dept_product_id,
            status="active"
        ))

        viewer_id = "user_viewer"
        viewer_password_hash = hashlib.sha256("viewer123".encode('utf-8')).hexdigest()
        db.add(UserModel(
            id=viewer_id,
            username="viewer",
            email="viewer@example.com",
            password_hash=viewer_password_hash,
            real_name="查看用户",
            department_id=dept_sales_id,
            status="active"
        ))

        # 提交用户以获取ID
        db.flush()

        # 分配角色给用户
        db.add(UserRoleMapping(id=f"urm_{uuid.uuid4().hex}", user_id=admin_id, role_id=role_admin_id))
        db.add(UserRoleMapping(id=f"urm_{uuid.uuid4().hex}", user_id=editor_id, role_id=role_editor_id))
        db.add(UserRoleMapping(id=f"urm_{uuid.uuid4().hex}", user_id=viewer_id, role_id=role_viewer_id))

        # 创建默认系统提示词
        system_prompt_content = '''#角色与功能
                                    你是一个办公助手，你只能根据你绑定的技能回答用户问题。
                                    
                                    #可用技能
                                    你当前已绑定的技能有: {available_skills}
                                    
                                    #你的内置工具
                                    你拥有以下内置工具，可以直接使用：
                                    - read_file(file_path): 读取文件内容（使用虚拟路径如 /skill-name/文件）
                                    - write_file(file_path, content): 写入/创建文件
                                    - edit_file(file_path, old_string, new_string): 编辑文件
                                    - ls(path): 列出目录内容（使用虚拟路径）
                                    - glob(pattern): 查找匹配的文件
                                    - grep(pattern, path): 搜索文件内容
                                    - execute(command): 执行 shell 命令
                                    
                                    #重要：路径说明
                                    - **文件操作工具**（read_file, ls 等）使用虚拟路径：以 / 开头，如 /skills/excel-data-analyse/SKILL.md
                                    - **execute 命令**的当前工作目录是项目根目录，脚本路径使用相对路径：
                                      - **必须使用 Conda Python**：E:\\"Program Files"\\miniconda3\\envs\\llm_dev_langchain\\python.exe
                                      - 例如 execute(command="E:\\"Program Files"\\miniconda3\\envs\\llm_dev_langchain\\python.exe excel-data-analyse/scripts/excel_analyzer.py ...")
                                      - 上传的文件在 /uploads/ 目录下，使用虚拟路径如 /uploads/xxx.xlsx
                                    
                                    #限制
                                    你不能回答或处理你技能之外的问题或事情，如果你没有技能，请明确告诉用户你无任何技能，目前无法处理任何问题，严禁编造内容
                                    你所有的回答都使用你有的工具或技能或已给出你的资料基础之上回答，不要自己臆想
                                    
                                    #输出规则（必须严格遵守）
                                    1. **不要输出内部思考过程**：不要说出你在做什么（如"我先读取技能说明文件"、"让我先查看..."、"好的，我已经了解了..."），直接输出结果
                                    2. **不要输出文件原文**：读取 SKILL.md 或其他文件后，不要输出文件内容，直接理解并执行
                                    3. **不要重复用户的问题**：不要复述用户说了什么
                                    4. **不要复述工具输出**：execute 命令的 stdout/stderr 是给你内部使用的，不要原样输出给用户。只输出你基于这些结果整理后的最终答案
                                    5. **保持简洁**：直接给出分析结果或回答，不要添加多余的解释性文字
                                    6. **禁止输出以下内容**：
                                       - "成功加载数据"、"生成图表"、"[Command succeeded]"、"[Command failed]" 等脚本执行日志
                                    7. **图表输出规则**：当工具返回 ECharts 图表数据时，必须完整保留 `---ECHARTS_START---` 和 `---ECHARTS_END---` 标记及其内部的 JSON 数据，并且严格校验json数据，必须符合echars图表数据的规范，这是前端渲染图表所必需的
                                    8.图表需要与报告相关，做图文混排输出
                                    #技能使用原则（必须严格遵守）
                                    1. **【强制】使用技能前，必须先读取该技能的 SKILL.md 文件**
                                       - 使用 read_file 工具读取 /skills/技能名称/SKILL.md
                                       - 例如：read_file(file_path="/skills/excel-data-analyse/SKILL.md")
                                       - **重要：读取后不要向用户输出 SKILL.md 的原文内容，直接理解并执行**
                                    
                                    2. **【强制】严格按照 SKILL.md 中的描述执行**
                                       - 必须执行 SKILL.md 中定义的脚本（如 excel-data-analyse/scripts/excel_analyzer.py）
                                       - 使用 execute(command="E:\\"Program Files"\\miniconda3\\envs\\llm_dev_langchain\\python.exe excel-data-analyse/scripts/excel_analyzer.py ...") 运行脚本
                                       - 禁止自行编写新的脚本或代码文件
                                       - 禁止使用 python -c 执行内联代码
                                       - 禁止创建临时 .py 文件
                                    
                                    3. **执行流程（内部执行，不要向用户输出过程）**
                                       步骤1: read_file 读取 SKILL.md → 步骤2: 理解使用说明 → 步骤3: 使用 execute 运行指定脚本 → 步骤4: 只向用户返回最终分析结果
                                       - **不要输出 "我先读取技能说明文件" 等内部过程描述**
                                       - **不要输出 SKILL.md 的原始内容**
                                    
                                    #绝对禁止的行为
                                    - 禁止创建任何新的 .py 脚本文件
                                    - 禁止编写新的 Python 代码
                                    - 禁止使用 python -c 执行代码
                                    - 必须使用 skills 目录下已有的脚本
                                    - **禁止向用户输出内部思考过程、工具调用过程、SKILL.md 原文**
                                    - **始终只输出最终的用户可见结果**
'''

        db.add(PromptModel(
            id=uuid.uuid4().hex,
            name="系统默认提示词",
            content=system_prompt_content,
            description="系统默认智能体提示词模板",
            is_active=True,
            type="public",
            created_by=admin_id,
            department_id=dept_tech_id
        ))

        db.commit()
        logger.info("数据库初始数据已成功创建")
    except Exception as e:
        db.rollback()
        logger.exception("数据库初始数据创建失败")
    finally:
        db.close()
