import os
import uuid
import shutil
import re
import yaml
import zipfile
import tempfile
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from dataaccess.database import SessionLocal
from dataaccess.skill_repo import SkillRepo
from dataaccess.role_repo import UserRoleRepo
from dataaccess.models import AgentSkillMappingModel, AgentModel
from utils.pagination import PageResult, paginate
from utils.logger import logger
from .llm import get_llm, get_llm_sync
from settings import skills_path
llm = get_llm()
# 用于简单同步调用的 LLM（不带 Langfuse 回调，避免流式追踪问题）
llm_sync = get_llm_sync()
class SkillService:
    """
    Skill管理服务类
    """

    SKILLS_DIR = Path(skills_path)

    @staticmethod
    def _get_session():
        return SessionLocal()

    @staticmethod
    def ensure_skills_dir():
        os.makedirs(SkillService.SKILLS_DIR, exist_ok=True)

    @staticmethod
    def sanitize_dirname(name: str) -> str:
        """清理目录名，移除非法字符"""
        if not name:
            return "unknown"
        # 替换非法字符为下划线
        sanitized = re.sub(r'[^\w\-_]', '_', str(name))
        # 移除连续的下划线
        sanitized = re.sub(r'_+', '_', sanitized)
        # 移除首尾下划线
        sanitized = sanitized.strip('_')
        return sanitized or "unknown"

    @staticmethod
    def _ensure_no_file_creation_rule(skill_dir: Path, skill_content: str) -> str:
        """
        确保无脚本技能包含'不得创建文件'的规则
        
        如果技能目录下没有 scripts 文件夹，则在 SKILL.md 中添加禁止创建文件的规则
        """
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists() and scripts_dir.is_dir():
            # 有脚本，不需要添加规则
            return skill_content
        
        # 无脚本，检查是否已有规则
        if "禁止创建任何文件" in skill_content or "不得创建文件" in skill_content:
            return skill_content
        
        # 在 YAML frontmatter 后添加规则
        rule_section = """

## ⚠️ 重要规则

**本技能没有脚本文件，所有内容必须直接输出到对话中，禁止创建任何文件（如.md、.txt、.py等）。**

**禁止使用 Write 工具创建文件，只能使用 Read 工具读取文件。**
"""
        
        # 找到 YAML frontmatter 的结束位置
        frontmatter_end = skill_content.find("\n---", 3)
        if frontmatter_end != -1:
            # 在 frontmatter 后插入规则
            insert_pos = frontmatter_end + 4
            return skill_content[:insert_pos] + rule_section + skill_content[insert_pos:]
        else:
            # 没有 frontmatter，在开头添加
            return "---\nname: skill\n---\n" + rule_section + "\n" + skill_content

    @staticmethod
    def _extract_yaml_description(markdown_content: str) -> str:
        """从SKILL.md的YAML frontmatter中提取description字段"""
        frontmatter_pattern = r"^---\s*\n(.*?)\n---"
        match = re.match(frontmatter_pattern, markdown_content, re.DOTALL)
        if match:
            try:
                data = yaml.safe_load(match.group(1))
                if isinstance(data, dict):
                    desc = data.get("description", "")
                    return str(desc).strip() if desc else ""
            except Exception:
                pass
        return ""

    @staticmethod
    def save_skill_config(skill_data: Dict[str, Any]) -> bool:
        skill_dir = None
        skill_id = None
        try:
            SkillService.ensure_skills_dir()
            skill_name = skill_data.get("name", "")
            if not skill_name:
                sanitized_name = skill_data.get("id", "")
            else:
                sanitized_name = SkillService.sanitize_dirname(skill_name).lower()

            # 1. 先生成唯一ID
            skill_id = skill_data.get("id", f"skill_{uuid.uuid4().hex}")

            # 2. 获取用户ID并清理
            user_id = skill_data.get("created_by", "unknown")
            sanitized_user_id = SkillService.sanitize_dirname(user_id)

            # 3. 创建技能文件夹 (使用用户隔离结构: skills/{user_id}/{name}/)
            skill_dir = SkillService.SKILLS_DIR / sanitized_user_id / sanitized_name
            os.makedirs(skill_dir, exist_ok=True)

            # 3. 生成SKILL.md内容
            prompt = PromptTemplate.from_template(
                """你是一个专业的AI技能定义专家。请根据用户提供的信息，按照Anthropic公司的技能定义标准，生成一个完整的、高质量的技能定义。

                    用户提供的技能信息：
                    - 技能名称（英文标识符）：{name}
                    - 技能描述：{description}
                    
                    请按照以下Anthropic技能标准格式输出：
                    
                    1. 首先是YAML frontmatter，包含name和description字段，使用 --- 作为分隔符
                    2. 然后是详细的技能定义内容，包括：
                       - 技能概述（详细说明技能的功能和价值）
                       - 使用场景（具体说明什么时候使用这个技能）
                       - 操作流程（详细的步骤说明）
                    
                    请确保生成的内容是一个完整的技能定义，而不是简单的描述。内容应该详细、结构化、专业，符合Anthropic的技能定义标准。
                    
                    重要规则（必须遵守）：
                    - YAML frontmatter 必须使用 --- 作为开始和结束标记
                    - name 字段必须严格使用：{name}
                    - description 字段应该简洁明了
                    - 其他内容使用中文
                    - **本技能没有脚本文件，所有内容必须直接输出到对话中，禁止创建任何文件（如.md、.txt、.py等）**
                    - **禁止使用 Write 工具创建文件，只能使用 Read 工具读取文件**
                    
                    示例格式：
                    ---
                    name: {name}
                    license: MIT
                    description: '技能描述'
                    ---
                    
                    # 技能标题
                    
                    ## 技能概述
                    ...
"""
            )

            try:
                generated_content = llm_sync.invoke(prompt.format(
                    name=skill_data.get('name', ''),
                    description=skill_data.get('description', '暂无描述')
                ))
                logger.info(f"LLM生成内容: {generated_content}")
                skill_content = generated_content.content
            except Exception as e:
                logger.warning(f"LLM生成失败，使用原始内容: {e}")
                skill_content = skill_data.get('code', '')

            # 4. 确保无脚本技能包含'不得创建文件'的规则
            skill_content = SkillService._ensure_no_file_creation_rule(skill_dir, skill_content)
            
            # 5. 写入SKILL.md
            markdown_file = skill_dir / "SKILL.md"
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(skill_content)

            # 5. 从生成的markdown中解析description
            description_from_md = SkillService._extract_yaml_description(skill_content)
            skill_path = str(markdown_file).replace('\\', '/')

            # 6. 写入数据库
            db = SkillService._get_session()
            try:
                db_skill = SkillRepo.create(db, {
                    "id": skill_id,
                    "skills_name": sanitized_name,
                    "skills_description": description_from_md or skill_data.get("description", ""),
                    "skills_path": skill_path,
                    "type": skill_data.get("skill_space", "private"),
                    "created_by": user_id,
                    "department_id": skill_data.get("department_id")
                })

                # 权限通过SkillModel的created_by和type字段控制
                # - type="private": 仅创建者可见（通过created_by判断）
                # - type="group": 同部门可见（需要结合部门信息判断）
                # - type="public": 所有人可见

                logger.info(f"技能已保存到数据库: {db_skill.id}")
                return True
            except Exception as db_e:
                logger.error(f"数据库写入失败: {db_e}")
                raise
            finally:
                db.close()

        except Exception as e:
            logger.error(f"保存Skill配置失败: {e}")
            logger.exception(e)
            if skill_dir and skill_dir.exists():
                shutil.rmtree(skill_dir)
                logger.info(f"已回滚删除文件夹: {skill_dir}")
            return False

    @staticmethod
    def get_skill_config(skill_id: str) -> Optional[Dict[str, Any]]:
        try:
            db = SkillService._get_session()
            try:
                skill = SkillRepo.get_by_id(db, skill_id)
                if not skill:
                    return None

                code = ""
                if skill.skills_path:
                    md_path = Path(skill.skills_path)
                    if md_path.exists():
                        code = md_path.read_text(encoding='utf-8')

                return {
                    "id": skill.id,
                    "name": skill.skills_name,
                    "displayName": skill.skills_name,
                    "description": skill.skills_description or "",
                    "code": code,
                    "skill_space": skill.type or "private",
                    "created_by": skill.created_by,
                    "createdAt": skill.created_at.isoformat() if skill.created_at else "",
                    "updatedAt": skill.updated_at.isoformat() if skill.updated_at else "",
                    "path": skill.skills_path or ""
                }
            finally:
                db.close()
        except Exception as e:
            logger.error(f"读取Skill配置失败: {e}")
            return None

    @staticmethod
    def list_all_skills(user_id: str = None, department_id: str = None) -> List[Dict[str, Any]]:
        """获取Skill列表（带空间过滤）"""
        try:
            db = SkillService._get_session()
            try:
                if user_id:
                    skills = SkillRepo.get_visible_skills(db, user_id, department_id)
                else:
                    skills = SkillRepo.get_all(db)
                result = []
                for skill in skills:
                    result.append({
                        "id": skill.id,
                        "name": skill.skills_name,
                        "displayName": skill.skills_name,
                        "description": skill.skills_description or "",
                        "code": "",
                        "skill_space": skill.type or "private",
                        "created_by": skill.created_by,
                        "createdAt": skill.created_at.isoformat() if skill.created_at else "",
                        "updatedAt": skill.updated_at.isoformat() if skill.updated_at else "",
                        "path": skill.skills_path or ""
                    })
                return result
            finally:
                db.close()
        except Exception as e:
            logger.error(f"获取Skill列表失败: {e}")
            logger.exception(e)
            return []

    @staticmethod
    def paginate_skills(page: int = 1, page_size: int = 10, user_id: str = None, department_id: str = None) -> dict:
        """分页获取技能列表（带空间过滤）"""
        try:
            db = SkillService._get_session()
            try:
                offset, limit = paginate(page, page_size)
                if user_id:
                    total = SkillRepo.count_visible_skills(db, user_id, department_id)
                    skills = SkillRepo.get_visible_skills_paginated(db, user_id, department_id, offset, limit)
                else:
                    total = SkillRepo.count_all(db)
                    skills = SkillRepo.get_all_paginated(db, offset, limit)
                items = []
                for skill in skills:
                    items.append({
                        "id": skill.id,
                        "name": skill.skills_name,
                        "displayName": skill.skills_name,
                        "description": skill.skills_description or "",
                        "code": "",
                        "skill_space": skill.type or "private",
                        "created_by": skill.created_by,
                        "createdAt": skill.created_at.isoformat() if skill.created_at else "",
                        "updatedAt": skill.updated_at.isoformat() if skill.updated_at else "",
                        "path": skill.skills_path or ""
                    })
                return PageResult(items, total, page, limit).to_dict()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"分页获取Skill列表失败: {e}")
            logger.exception(e)
            return PageResult([], 0, page, page_size).to_dict()

    @staticmethod
    def get_skills_by_ids(skill_ids: List[str]) -> List[Dict[str, Any]]:
        """根据技能ID列表获取匹配的技能信息（兼容按名称匹配）

        Args:
            skill_ids: 技能ID列表，优先按 skill.id 匹配，兼容旧数据按 skill.name 匹配

        Returns:
            匹配到的技能列表
        """
        all_skills = SkillService.list_all_skills()
        skill_by_id = {s["id"]: s for s in all_skills}
        skill_by_name = {s["name"]: s for s in all_skills}

        matched = []
        for sid in skill_ids:
            skill = skill_by_id.get(sid) or skill_by_name.get(sid)
            if skill:
                matched.append(skill)
        return matched

    @staticmethod
    def get_skill_source_paths(skill_ids: List[str]) -> List[str]:
        """将技能ID列表转换为技能目录源路径列表（用于DeepAgent）

        Args:
            skill_ids: 技能ID列表

        Returns:
            技能目录源路径列表，格式如 ["/skills/{user_id}/excel-data-analyse/"]
        """
        skills = SkillService.get_skills_by_ids(skill_ids)
        # 使用虚拟路径格式（以/开头），FilesystemBackend 会将其映射到实际路径
        # 技能路径现在包含用户ID: skills/{user_id}/{skill_name}/
        return [f"/skills/{SkillService.sanitize_dirname(s.get('created_by', 'unknown'))}/{s['name']}/" for s in skills]

    @staticmethod
    def update_skill_config(skill_id: str, update_data: Dict[str, Any]) -> bool:
        try:
            db = SkillService._get_session()
            try:
                update_dict = {}
                if "name" in update_data:
                    update_dict["skills_name"] = update_data["name"]
                if "description" in update_data:
                    update_dict["skills_description"] = update_data["description"]
                if "path" in update_data:
                    update_dict["skills_path"] = update_data["path"]
                # 支持 type 或 skill_space 字段
                if "type" in update_data:
                    update_dict["type"] = update_data["type"]

                if update_dict:
                    skill = SkillRepo.update(db, skill_id, update_dict)
                    return skill is not None
                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"更新Skill配置失败: {e}")
            return False

    @staticmethod
    def update_skill_with_file(skill_id: str, update_data: Dict[str, Any]) -> bool:
        """更新技能，同时修改数据库信息和SKILL.md文件内容

        Args:
            skill_id: 技能ID
            update_data: 更新数据，可包含 name, description, code(code将写入SKILL.md)

        Returns:
            是否成功
        """
        try:
            # 1. 读取现有技能信息
            db = SkillService._get_session()
            try:
                existing = SkillRepo.get_by_id(db, skill_id)
                if not existing:
                    logger.warning(f"技能不存在: {skill_id}")
                    return False

                # 2. 如果有code，先重写SKILL.md文件
                if "code" in update_data and update_data["code"] is not None:
                    md_path = existing.skills_path
                    if md_path:
                        md_file = Path(md_path)
                        if not md_file.parent.exists():
                            md_file.parent.mkdir(parents=True, exist_ok=True)
                        md_file.write_text(update_data["code"], encoding='utf-8')
                        logger.info(f"SKILL.md文件已更新: {md_path}")

                # 3. 更新数据库
                update_dict = {}
                if "name" in update_data:
                    update_dict["skills_name"] = update_data["name"]
                if "description" in update_data:
                    update_dict["skills_description"] = update_data["description"]
                # 可见范围 - 支持 type 或 skill_space 字段
                if "type" in update_data:
                    update_dict["type"] = update_data["type"]

                if update_dict:
                    updated = SkillRepo.update(db, skill_id, update_dict)
                    return updated is not None

                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"更新Skill(含文件)失败: {e}")
            logger.exception(e)
            return False

    @staticmethod
    def delete_skill_config(skill_id: str, user_id: str = None) -> Dict[str, Any]:
        try:
            db = SkillService._get_session()
            try:
                skill = SkillRepo.get_by_id(db, skill_id)
                if not skill:
                    return {"success": False, "message": "Skill不存在"}

                # 权限检查：只有创建者或管理员可以删除
                if user_id:
                    is_admin = UserRoleRepo.is_user_admin(db, user_id)
                    if skill.created_by != user_id and not is_admin:
                        return {"success": False, "message": "无权删除，仅本人或管理员可以删除"}

                # 检查是否有Agent引用此Skill
                ref_count = SkillRepo.count_agent_references(db, skill_id)
                if ref_count > 0:
                    agent_names = db.query(AgentModel.name).join(
                        AgentSkillMappingModel,
                        AgentModel.agent_id == AgentSkillMappingModel.agent_id
                    ).filter(
                        AgentSkillMappingModel.skills_id == skill_id
                    ).all()
                    names = [n[0] for n in agent_names if n[0]]
                    return {
                        "success": False,
                        "message": f"Skill「{skill.skills_name}」被 {ref_count} 个智能体引用（{', '.join(names)}），无法删除，请先移除智能体中的引用"
                    }

                skill_name = skill.skills_name
                skill_user_id = skill.created_by or "unknown"
                sanitized_skill_user_id = SkillService.sanitize_dirname(skill_user_id)
                result = SkillRepo.delete(db, skill_id)

                if result and skill_name:
                    skill_dir = SkillService.SKILLS_DIR / sanitized_skill_user_id / skill_name
                    if skill_dir.exists():
                        shutil.rmtree(skill_dir)
                        logger.info(f"已删除技能文件夹: {skill_dir}")

                return {"success": True, "message": "删除成功"}
            finally:
                db.close()
        except Exception as e:
            logger.error(f"删除Skill配置失败: {e}")
            logger.exception(e)
            return {"success": False, "message": f"删除失败: {str(e)}"}

    @staticmethod
    def export_skills_zip() -> str:
        """将所有技能导出为ZIP文件，返回临时ZIP文件路径"""
        skills = SkillService.list_all_skills()
        tmp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        tmp_zip_path = tmp_zip.name
        tmp_zip.close()

        with zipfile.ZipFile(tmp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            meta = []
            for sk in skills:
                name = sk["name"]
                meta.append({"id": sk["id"], "name": name, "description": sk["description"]})
                skill_dir = SkillService.SKILLS_DIR / name
                if not skill_dir.exists():
                    continue
                inner_dir = skill_dir / name
                source_dir = inner_dir if inner_dir.exists() else skill_dir
                for file_path in source_dir.rglob('*'):
                    if file_path.is_file():
                        rel = str(file_path.relative_to(source_dir))
                        zf.write(file_path, f"{name}/{rel}")
            zf.writestr('_skills_meta.json', json.dumps(meta, ensure_ascii=False, indent=2))

        return tmp_zip_path

    @staticmethod
    def export_single_skill_zip(skill_id: str) -> Optional[Dict[str, Any]]:
        """导出单个技能为扁平ZIP文件，返回 {zip_path, filename}，失败返回None

        ZIP格式：根目录下平铺 SKILL.md + 其他所有文件 + _skills_meta.json, 无子目录
        """
        skills = SkillService.list_all_skills()
        target_skill = None
        for sk in skills:
            if sk["id"] == skill_id:
                target_skill = sk
                break
        if not target_skill:
            return None

        name = target_skill["name"]
        display_name = target_skill.get("displayName") or name

        skill_detail = SkillService.get_skill_config(skill_id)
        if not skill_detail:
            return None

        md_content = skill_detail.get("code", "")

        tmp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        tmp_zip_path = tmp_zip.name
        tmp_zip.close()

        skill_inner_dir = SkillService.SKILLS_DIR / name / name

        with zipfile.ZipFile(tmp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            if md_content:
                zf.writestr("SKILL.md", md_content)
            else:
                fallback = f"# {display_name}\n\n{target_skill.get('description', '')}"
                zf.writestr("SKILL.md", fallback)

            if skill_inner_dir.exists():
                for file_path in skill_inner_dir.rglob('*'):
                    if file_path.is_file() and file_path.name.lower() != "skill.md":
                        rel = str(file_path.relative_to(skill_inner_dir))
                        zf.write(file_path, rel)

            meta = [{"id": target_skill["id"], "name": name, "description": target_skill["description"]}]
            zf.writestr('_skills_meta.json', json.dumps(meta, ensure_ascii=False, indent=2))

        return {"zip_path": tmp_zip_path, "filename": f"{display_name}.zip"}

    @staticmethod
    def import_skills_zip(zip_path: str, original_filename: str = None, user_id: str = None, department_id: str = None) -> Dict[str, Any]:
        """从ZIP文件导入技能，返回导入结果统计

        Args:
            zip_path: ZIP文件路径
            original_filename: 原始上传文件名（不含路径），用于提取技能名称
            user_id: 导入者用户ID
            department_id: 导入者部门ID
        """
        result = {"success": 0, "skipped": 0, "errors": []}
        extract_dir = tempfile.mkdtemp()

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            extract_path = Path(extract_dir)

            meta = None
            meta_file = extract_path / '_skills_meta.json'
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding='utf-8'))
                meta_map = {m["name"]: m for m in meta} if meta else {}
            else:
                meta_map = {}

            db = SkillService._get_session()
            try:
                for item in extract_path.iterdir():
                    if not item.is_dir():
                        continue
                    name = item.name
                    if name.startswith('__') or name.startswith('.'):
                        continue
                    existing = SkillRepo.get_by_name(db, name)
                    if existing:
                        result["skipped"] += 1
                        continue

                    md_file = item / name / "SKILL.md"
                    if not md_file.exists():
                        md_file = item / "SKILL.md"
                    if not md_file.exists():
                        continue

                    skill_content = md_file.read_text(encoding='utf-8')
                    description = SkillService._extract_yaml_description(skill_content)
                    meta_info = meta_map.get(name, {})
                    desc = description or meta_info.get("description", "")

                    new_id = f"skill_{uuid.uuid4().hex}"
                    # 使用用户隔离结构: skills/{user_id}/{name}/
                    sanitized_import_user_id = SkillService.sanitize_dirname(user_id)
                    dest_dir = SkillService.SKILLS_DIR / sanitized_import_user_id / name
                    dest_dir.mkdir(parents=True, exist_ok=True)

                    src_md = item / name / "SKILL.md" if (item / name / "SKILL.md").exists() else item / "SKILL.md"
                    if src_md.parent.name == name:
                        # 复制整个目录内容到目标目录
                        for src_file in src_md.parent.iterdir():
                            dest_file = dest_dir / src_file.name
                            if src_file.is_dir():
                                shutil.copytree(src_file, dest_file, dirs_exist_ok=True)
                            else:
                                shutil.copy2(src_file, dest_file)
                    else:
                        shutil.copy2(src_md, dest_dir / "SKILL.md")

                    # 确保无脚本技能包含'不得创建文件'的规则
                    dest_md = dest_dir / "SKILL.md"
                    if dest_md.exists():
                        skill_content = dest_md.read_text(encoding='utf-8')
                        updated_content = SkillService._ensure_no_file_creation_rule(dest_dir, skill_content)
                        if updated_content != skill_content:
                            dest_md.write_text(updated_content, encoding='utf-8')
                            logger.info(f"已为导入的技能 {name} 添加'不得创建文件'规则")

                    skill_path = str(dest_dir / "SKILL.md").replace('\\', '/')

                    SkillRepo.create(db, {
                        "id": new_id,
                        "skills_name": name,
                        "skills_description": desc,
                        "skills_path": skill_path,
                        "type": "private",
                        "created_by": user_id,
                        "department_id": department_id
                    })
                    result["success"] += 1

                md_at_root = extract_path / "SKILL.md"
                if md_at_root.exists():
                    skill_name = ""
                    if original_filename:
                        skill_name = Path(original_filename).stem
                    if not skill_name and meta and len(meta) > 0:
                        skill_name = meta[0].get("name", "")

                    if skill_name:
                        sanitized = SkillService.sanitize_dirname(skill_name).lower()
                        existing = SkillRepo.get_by_name(db, sanitized)
                        if existing:
                            result["skipped"] += 1
                        else:
                            content = md_at_root.read_text(encoding='utf-8')
                            description = SkillService._extract_yaml_description(content)
                            if not description and meta and len(meta) > 0:
                                description = meta[0].get("description", "")

                            new_id = f"skill_{uuid.uuid4().hex}"
                            # 使用用户隔离结构: skills/{user_id}/{sanitized}/
                            sanitized_import_user_id2 = SkillService.sanitize_dirname(user_id)
                            dest_dir = SkillService.SKILLS_DIR / sanitized_import_user_id2 / sanitized
                            dest_dir.mkdir(parents=True, exist_ok=True)

                            for src_file in extract_path.iterdir():
                                if src_file.name == '_skills_meta.json' or src_file.name.startswith('__') or src_file.name.startswith('.'):
                                    continue
                                dest = dest_dir / src_file.name
                                if src_file.is_dir():
                                    shutil.copytree(src_file, dest, dirs_exist_ok=True)
                                else:
                                    shutil.copy2(src_file, dest)

                            # 确保无脚本技能包含'不得创建文件'的规则
                            dest_md = dest_dir / "SKILL.md"
                            if dest_md.exists():
                                skill_content = dest_md.read_text(encoding='utf-8')
                                updated_content = SkillService._ensure_no_file_creation_rule(dest_dir, skill_content)
                                if updated_content != skill_content:
                                    dest_md.write_text(updated_content, encoding='utf-8')
                                    logger.info(f"已为导入的技能 {sanitized} 添加'不得创建文件'规则")

                            skill_path = str(dest_dir / "SKILL.md").replace('\\', '/')

                            SkillRepo.create(db, {
                                "id": new_id,
                                "skills_name": sanitized,
                                "skills_description": description,
                                "skills_path": skill_path,
                                "type": "private",
                                "created_by": user_id,
                                "department_id": department_id
                            })
                            result["success"] += 1

                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        except Exception as e:
            result["errors"].append(str(e))
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)

        return result
    @staticmethod
    def generate_english_name(chinese_name: str, description: str = "") -> str:
        """
        使用LLM将中文技能名称转换为符合Agent Skills规范的英文名称

        Args:
            chinese_name: 中文技能名称
            description: 技能描述（可选，用于辅助生成更准确的英文名称）

        Returns:
            str: 符合规范的英文名称（小写字母、数字和连字符）
        """
        # 如果名称已经是英文格式，直接清理返回
        if re.match(r'^[a-zA-Z0-9\-]+$', chinese_name):
            return chinese_name.lower().strip('-')

        prompt = PromptTemplate.from_template(
            """请将以下中文技能名称转换为符合Agent Skills规范的英文标识符。

    要求：
    1. 使用小写字母、数字和连字符（-）
    2. 简洁明了，2-4个单词
    3. 使用kebab-case格式（如：web-research, code-review）
    4. 不要使用空格或下划线
    5. 不要使用特殊字符

    中文技能名称：{name}
    技能描述：{description}

    请只返回英文标识符，不要有任何其他内容。

    示例：
    - "小说创作" -> "novel-writing"
    - "代码审查" -> "code-review"
    - "Web搜索研究" -> "web-research"
    - "内容要点提取" -> "content-extraction"
    """
        )

        try:
            result = llm_sync.invoke(prompt.format(
                name=chinese_name,
                description=description or "暂无描述"
            ))
            english_name = result.content.strip().lower()

            # 清理生成的名称，确保符合规范
            english_name = re.sub(r'[^a-z0-9\-]', '-', english_name)
            english_name = re.sub(r'-+', '-', english_name)
            english_name = english_name.strip('-')

            if english_name:
                return english_name
        except Exception as e:
            logger.warning(f"生成英文名称失败: {e}")

        # 如果生成失败，使用简单的清理方式
        sanitized = re.sub(r'[^a-zA-Z0-9\-]', '-', chinese_name)
        sanitized = sanitized.lower()
        sanitized = re.sub(r'-+', '-', sanitized)
        sanitized = sanitized.strip('-')
        return sanitized or "skill"
