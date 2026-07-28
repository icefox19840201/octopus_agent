import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from dataaccess.database import Base


class AgentModel(Base):
    __tablename__ = "agents"

    agent_id = Column(String(40), primary_key=True, comment="智能体Id")
    name = Column(String(100), nullable=False, comment="智能体名称")
    description = Column(String(255), nullable=True, comment="智能体描述")
    status = Column(Integer, nullable=True, default=1, comment="智能体状态，1：正常，0：报错")
    config = Column(Text, nullable=True, comment="智能体配置(JSON)")
    temperature = Column(Float, nullable=True, default=0.7, comment="模型温度值，控制输出随机性")
    top_p = Column(Float, nullable=True, default=0.9, comment="模型多样性参数")
    enable_memory = Column(Boolean, nullable=True, default=True, comment="是否启用记忆功能")
    model_id = Column(String(40), ForeignKey("llm_models.id", ondelete="SET NULL"), nullable=True, comment="关联模型ID")
    prompt_id = Column(String(40), ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True, comment="关联提示词ID")
    created_by = Column(String(40), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建者用户ID")
    department_id = Column(String(40), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="所属部门ID")
    type=Column(String(10),nullable=True,comment='public：所有人可见，private:仅自己可见：group：同部门可见')
    is_locked = Column(Boolean, nullable=True, default=False, comment="是否锁定配置，True时仅创建人可修改")
    # 关系
    skill_mappings = relationship("AgentSkillMappingModel", back_populates="agent", cascade="all, delete-orphan")
    tool_mappings = relationship("AgentToolMappingModel", back_populates="agent", cascade="all, delete-orphan")
    model = relationship("LLMModel", back_populates="agents")
    prompt = relationship("PromptModel", back_populates="agents")
    creator = relationship("UserModel", back_populates="created_agents")
    department = relationship("DepartmentModel", back_populates="agents")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class SkillModel(Base):
    __tablename__ = "skills"

    id = Column(String(40), primary_key=True, comment="主键")
    skills_name = Column(String(255), nullable=True, comment="技能名称")
    skills_description = Column(Text, nullable=True, comment="技能描述")
    skills_path = Column(String(255), nullable=True, comment="技能路径")
    created_by = Column(String(40), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建者用户ID")
    department_id = Column(String(40), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="所属部门ID")
    type = Column(String(10), nullable=True, comment='public：所有人可见，private:仅自己可见：group：同部门可见')
    # 关系
    agent_mappings = relationship("AgentSkillMappingModel", back_populates="skill", cascade="all, delete-orphan")
    creator = relationship("UserModel", back_populates="created_skills")
    department = relationship("DepartmentModel", back_populates="skills")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class AgentSkillMappingModel(Base):
    __tablename__ = "agent_skills_mapping"

    id = Column(String(32), primary_key=True, comment="主键")
    agent_id = Column(String(40), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False, comment="智能体id")
    skills_id = Column(String(40), ForeignKey("skills.id", ondelete="CASCADE"), nullable=True, comment="技能id")
    agent = relationship("AgentModel", back_populates="skill_mappings")
    skill = relationship("SkillModel", back_populates="agent_mappings")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class AgentToolMappingModel(Base):
    """Agent与MCP工具关联表"""
    __tablename__ = "agent_tools_mapping"

    id = Column(String(32), primary_key=True, comment="主键")
    agent_id = Column(String(40), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False, comment="智能体ID")
    tool_id = Column(String(40), ForeignKey("mcp_tools.id", ondelete="CASCADE"), nullable=False, comment="工具ID")
    agent = relationship("AgentModel", back_populates="tool_mappings")
    tool = relationship("MCPToolModel", back_populates="agent_mappings")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class DepartmentModel(Base):
    """部门模型"""
    __tablename__ = "departments"

    id = Column(String(40), primary_key=True, comment="主键")
    name = Column(String(100), nullable=False, comment="部门名称")
    code = Column(String(50), unique=True, nullable=False, comment="部门编码")
    parent_id = Column(String(40), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="父部门ID")
    description = Column(String(255), nullable=True, comment="部门描述")
    sort_order = Column(Integer, nullable=True, default=0, comment="排序顺序")
    status = Column(String(20), nullable=True, default="active", comment="状态：active启用，inactive停用")

    # 自关联关系
    parent = relationship("DepartmentModel", remote_side=[id], backref="children")
    # 用户关系
    users = relationship("UserModel", back_populates="department")
    # 智能体和技能关系（部门共享资源）
    agents = relationship("AgentModel", back_populates="department")
    skills = relationship("SkillModel", back_populates="department")
    mcps = relationship("MCPModel", back_populates="department")
    prompts = relationship("PromptModel", back_populates="department")
    knowledge_bases = relationship("KnowledgeBaseModel", back_populates="department")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(40), primary_key=True, comment="主键")
    username = Column(String(100), unique=True, nullable=False, comment="用户名")
    email = Column(String(255), nullable=True, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(100), nullable=True, comment="真实姓名")
    phone = Column(String(20), nullable=True, comment="手机号")
    department_id = Column(String(40), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="所属部门ID")
    status = Column(String(20), nullable=True, default="active", comment="状态：active激活，inactive停用")

    # 关系
    department = relationship("DepartmentModel", back_populates="users")
    role_mappings = relationship("UserRoleMapping", back_populates="user", cascade="all, delete-orphan")
    created_agents = relationship("AgentModel", back_populates="creator")
    created_skills = relationship("SkillModel", back_populates="creator")
    created_mcps = relationship("MCPModel", back_populates="creator")
    created_prompts = relationship("PromptModel", back_populates="creator")
    created_knowledge_bases = relationship("KnowledgeBaseModel", back_populates="creator")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(String(40), primary_key=True, comment="主键")
    name = Column(String(100), unique=True, nullable=False, comment="角色名称")
    code = Column(String(50), unique=True, nullable=False, comment="角色编码")
    description = Column(String(255), nullable=True, comment="角色描述")
    status = Column(String(20), nullable=True, default="active", comment="状态：active启用，inactive停用")
    # 关系
    user_mappings = relationship("UserRoleMapping", back_populates="role", cascade="all, delete-orphan")
    permission_mappings = relationship("RolePermissionMapping", back_populates="role", cascade="all, delete-orphan")

    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class PermissionModel(Base):
    __tablename__ = "permissions"

    id = Column(String(40), primary_key=True, comment="主键")
    key = Column(String(100), unique=True, nullable=False, comment="权限标识")
    name = Column(String(100), nullable=False, comment="权限名称")
    is_menu = Column(Boolean, nullable=True, default=False, comment="是否为菜单权限")
    menu_path = Column(String(100), nullable=True, comment="菜单路径/页面标识，如: dashboard, agents")
    menu_icon = Column(String(50), nullable=True, comment="菜单图标")
    menu_order = Column(Integer, nullable=True, default=0, comment="菜单排序")
    status = Column(String(20), nullable=True, default="active", comment="状态：active启用，inactive停用")
    # 关系
    role_mappings = relationship("RolePermissionMapping", back_populates="permission", cascade="all, delete-orphan")

    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")




class UserRoleMapping(Base):
    """用户角色关联表"""
    __tablename__ = "user_roles"

    id = Column(String(40), primary_key=True, comment="主键")
    user_id = Column(String(40), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    role_id = Column(String(40), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, comment="角色ID")

    # 关系
    user = relationship("UserModel", back_populates="role_mappings")
    role = relationship("RoleModel", back_populates="user_mappings")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")

class RolePermissionMapping(Base):
    __tablename__ = "role_permissions"

    id = Column(String(40), primary_key=True, comment="主键")
    role_id = Column(String(40), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, comment="角色id")
    permission_id = Column(String(40), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, comment="权限id")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")

    # 关系
    role = relationship("RoleModel", back_populates="permission_mappings")
    permission = relationship("PermissionModel", back_populates="role_mappings")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(String(40), primary_key=True, comment="主键")
    agent_id = Column(String(40), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False, comment="智能体id")
    user_id = Column(String(40), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户id")
    user_message = Column(Text, nullable=False, comment="用户消息")
    ai_message = Column(Text, nullable=False, comment="AI回复消息")
    conversation_id = Column(String(100), nullable=True, comment="对话会话ID")

    agent = relationship("AgentModel")
    user = relationship("UserModel")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")


class LLMModel(Base):
    """LLM模型配置表"""
    __tablename__ = "llm_models"

    id = Column(String(40), primary_key=True, comment="模型ID")
    name = Column(String(100), nullable=False, comment="显示名称")
    model_type = Column(String(20), nullable=False, default="chat", comment="模型类型：chat对话模型，embedding嵌入模型，huggingface")
    provider = Column(String(50), nullable=False, default="openai", comment="提供商：openai, anthropic, azure, ollama, huggingface, custom")
    model_name = Column(String(100), nullable=False, comment="模型名称/ID，如gpt-4o")
    base_url = Column(String(255), nullable=True, comment="接口地址")
    api_key = Column(String(255), nullable=True, comment="API密钥")
    description = Column(String(500), nullable=True, comment="描述")
    status = Column(String(20), nullable=True, default="stopped", comment="状态：active运行中，stopped已停止")
    # 关系
    agents = relationship("AgentModel", back_populates="model")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class MCPModel(Base):
    """MCP服务配置表"""
    __tablename__ = "mcp_servers"

    id = Column(String(40), primary_key=True, comment="MCP服务ID")
    name = Column(String(100), nullable=False, comment="服务名称")
    type = Column(String(20), nullable=False, default="sse", comment="服务类型：sse, stdio, streamable-http")
    endpoint = Column(String(500), nullable=False, comment="端点地址或命令")
    description = Column(String(500), nullable=True, comment="描述")
    visibility = Column(String(10), nullable=False, default="private", comment="可见性：public所有人可见，private仅自己可见，group同部门可见")
    created_by = Column(String(40), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建者用户ID")
    department_id = Column(String(40), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="所属部门ID")
    status = Column(String(20), nullable=True, default="stopped", comment="状态：active正常，stopped停止")
    
    # 关系
    creator = relationship("UserModel", back_populates="created_mcps")
    department = relationship("DepartmentModel", back_populates="mcps")
    tools = relationship("MCPToolModel", back_populates="mcp_server", cascade="all, delete-orphan")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class MCPToolModel(Base):
    """MCP工具表"""
    __tablename__ = "mcp_tools"

    id = Column(String(40), primary_key=True, comment="工具ID")
    mcp_id = Column(String(40), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False, comment="所属MCP服务ID")
    name = Column(String(100), nullable=False, comment="工具名称")
    description = Column(String(500), nullable=True, comment="工具描述")
    parameters = Column(Text, nullable=True, comment="工具参数Schema(JSON)")

    # 关系
    mcp_server = relationship("MCPModel", back_populates="tools")
    agent_mappings = relationship("AgentToolMappingModel", back_populates="tool", cascade="all, delete-orphan")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class PromptModel(Base):
    """提示词管理表"""
    __tablename__ = "prompts"

    id = Column(String(40), primary_key=True, comment="主键")
    name = Column(String(100), nullable=False, comment="提示词名称")
    content = Column(Text, nullable=False, comment="提示词内容")
    description = Column(String(500), nullable=True, comment="提示词描述")
    is_active = Column(Boolean, nullable=True, default=True, comment="是否启用")
    created_by = Column(String(40), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建者用户ID")
    department_id = Column(String(40), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="所属部门ID")
    type = Column(String(10), nullable=True, default="private", comment="可见性：public所有人可见，private仅自己可见，group同部门可见")

    # 关系
    creator = relationship("UserModel", back_populates="created_prompts")
    department = relationship("DepartmentModel", back_populates="prompts")
    agents = relationship("AgentModel", back_populates="prompt")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class KnowledgeBaseModel(Base):
    """知识库管理表"""
    __tablename__ = "knowledge_bases"

    id = Column(String(40), primary_key=True, comment="主键")
    name = Column(String(100), nullable=False, comment="知识库名称")
    description = Column(String(500), nullable=True, comment="知识库描述")
    embedding_model = Column(String(100), nullable=True, comment="嵌入模型名称")
    vector_store_path = Column(String(255), nullable=True, comment="向量存储路径")
    type = Column(String(10), nullable=True, default="private", comment="可见性：public所有人可见，private仅自己可见，group同部门可见")
    created_by = Column(String(40), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建者用户ID")
    department_id = Column(String(40), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="所属部门ID")
    status = Column(String(20), nullable=True, default="active", comment="状态：active启用，inactive停用")

    # 关系
    creator = relationship("UserModel", back_populates="created_knowledge_bases")
    department = relationship("DepartmentModel", back_populates="knowledge_bases")
    documents = relationship("KnowledgeDocumentModel", back_populates="knowledge_base", cascade="all, delete-orphan")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")


class KnowledgeDocumentModel(Base):
    """知识库文档表"""
    __tablename__ = "knowledge_documents"

    id = Column(String(40), primary_key=True, comment="主键")
    kb_id = Column(String(40), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, comment="所属知识库ID")
    title = Column(String(255), nullable=False, comment="文档标题")
    content = Column(Text, nullable=True, comment="文档内容")
    file_path = Column(String(255), nullable=True, comment="文件路径")
    file_type = Column(String(50), nullable=True, comment="文件类型")
    chunk_count = Column(Integer, nullable=True, default=0, comment="分块数量")
    status = Column(String(20), nullable=True, default="active", comment="状态：active启用，inactive停用")

    # 关系
    knowledge_base = relationship("KnowledgeBaseModel", back_populates="documents")
    created_at = Column(DateTime, nullable=True, default=datetime.now, comment="创建日期")
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now, comment="更新日期")
