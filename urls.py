from fastapi import APIRouter
from views.default_viewer import default
from views.agent_view import create_agent, list_agents, get_agent, update_agent, delete_agent, export_agents, import_agents, export_single_agent
from views.skill_view import create_skill, list_skills, get_skill, update_skill, delete_skill, export_skills, import_skills, export_single_skill
from views.chat_view import chat, get_chat_history
from views.upload_view import upload_file, upload_multiple_files
from views.auth_view import login, logout, verify, change_password
from views.user_view import create_user as user_create, list_users as user_list, get_user as user_get, update_user as user_update, delete_user as user_delete
from views.department_view import create_department as dept_create, list_departments as dept_list, get_department_tree as dept_tree, get_department as dept_get, update_department as dept_update, delete_department as dept_delete
from views.role_view import create_role as role_create, list_roles as role_list, get_role as role_get, update_role as role_update, delete_role as role_delete, get_role_permissions as role_get_perms, set_role_permissions as role_set_perms
from views.permission_view import create_permission as perm_create, list_permissions as perm_list, get_permission_list_simple as perm_list_simple, init_default_permissions as perm_init, get_permission as perm_get, update_permission as perm_update, delete_permission as perm_delete, get_user_menus as perm_user_menus
from views.model_view import create_model as model_create, list_models as model_list, get_model as model_get, update_model as model_update, delete_model as model_delete, test_model_connection as model_test
from views.mcp_view import create_mcp as mcp_create, list_mcps as mcp_list, get_mcp as mcp_get, update_mcp as mcp_update, delete_mcp as mcp_delete, sync_mcp_tools as mcp_sync, list_mcp_tools as mcp_tools_list, invoke_mcp_tool as mcp_tool_invoke, get_all_mcp_tools as mcp_all_tools
from views.prompt_view import create_prompt as prompt_create, list_prompts as prompt_list, get_prompt as prompt_get, update_prompt as prompt_update, delete_prompt as prompt_delete
from views.knowledge_base_view import (
    create_knowledge_base as kb_create,
    list_knowledge_bases as kb_list,
    get_knowledge_base as kb_get,
    update_knowledge_base as kb_update,
    delete_knowledge_base as kb_delete,
    create_document as doc_create,
    list_documents as doc_list,
    delete_document as doc_delete, docs2_milvusdb
)
from views.model_view import get_active_models as model_active_list
from views.dashboard_view import (
    get_dashboard_overview as dashboard_overview,
    get_dashboard_full as dashboard_full,
    get_agent_stats as dashboard_agent_stats,
    get_skill_stats as dashboard_skill_stats,
    get_mcp_stats as dashboard_mcp_stats,
    get_chat_stats as dashboard_chat_stats,
    get_recent_activities as dashboard_activities,
    get_popular_stats as dashboard_popular,
    get_daily_trend as dashboard_daily_trend,
    get_dashboard_complete as dashboard_complete
)

sys_router = APIRouter()

# 页面路由
sys_router.add_api_route('/index', default, methods=["GET"], tags=["页面"], description="默认页面")

# 认证API路由
sys_router.add_api_route('/auth/login', login, methods=["POST"], tags=["认证"], description="用户登录")
sys_router.add_api_route('/auth/logout', logout, methods=["POST"], tags=["认证"], description="用户登出")
sys_router.add_api_route('/auth/verify', verify, methods=["GET"], tags=["认证"], description="验证用户登录状态")
sys_router.add_api_route('/auth/change-password', change_password, methods=["POST"], tags=["认证"], description="修改用户密码")

# Agent管理API路由
sys_router.add_api_route('/agents/create', create_agent, methods=["POST"], tags=["Agent管理"], description="创建Agent")
sys_router.add_api_route('/agents/list', list_agents, methods=["GET"], tags=["Agent管理"], description="获取Agent列表")
sys_router.add_api_route('/agents/export', export_agents, methods=["GET"], tags=["Agent管理"], description="导出所有Agent")
sys_router.add_api_route('/agents/import', import_agents, methods=["POST"], tags=["Agent管理"], description="导入Agent")
sys_router.add_api_route('/agents/{agent_id}/export', export_single_agent, methods=["GET"], tags=["Agent管理"], description="导出单个Agent")
sys_router.add_api_route('/agents/{agent_id}', get_agent, methods=["GET"], tags=["Agent管理"], description="获取Agent详情")
sys_router.add_api_route('/agents/{agent_id}', update_agent, methods=["PUT"], tags=["Agent管理"], description="更新Agent")
sys_router.add_api_route('/agents/{agent_id}', delete_agent, methods=["DELETE"], tags=["Agent管理"], description="删除Agent")

# Skill管理API路由
sys_router.add_api_route('/skills/create', create_skill, methods=["POST"], tags=["Skill管理"], description="创建Skill")
sys_router.add_api_route('/skills/list', list_skills, methods=["GET"], tags=["Skill管理"], description="获取Skill列表")
sys_router.add_api_route('/skills/export', export_skills, methods=["GET"], tags=["Skill管理"], description="导出所有Skill")
sys_router.add_api_route('/skills/import', import_skills, methods=["POST"], tags=["Skill管理"], description="导入Skill")
sys_router.add_api_route('/skills/{skill_id}/export', export_single_skill, methods=["GET"], tags=["Skill管理"], description="导出单个Skill")
sys_router.add_api_route('/skills/{skill_id}', get_skill, methods=["GET"], tags=["Skill管理"], description="获取Skill详情")
sys_router.add_api_route('/skills/{skill_id}', update_skill, methods=["PUT"], tags=["Skill管理"], description="更新Skill")
sys_router.add_api_route('/skills/{skill_id}', delete_skill, methods=["DELETE"], tags=["Skill管理"], description="删除Skill")

# 聊天接口
sys_router.add_api_route('/chat', chat, methods=["POST"], tags=["聊天"], description="智能体聊天接口")
sys_router.add_api_route('/chat/history', get_chat_history, methods=["GET"], tags=["聊天"], description="获取对话历史")

# 文件上传接口
sys_router.add_api_route('/upload', upload_file, methods=["POST"], tags=["文件上传"], description="上传单个文件")
sys_router.add_api_route('/upload/batch', upload_multiple_files, methods=["POST"], tags=["文件上传"], description="批量上传文件")

# 权限管理路由 
sys_router.add_api_route('/users', user_create, methods=["POST"], tags=["用户管理"], description="创建用户")
sys_router.add_api_route('/users', user_list, methods=["GET"], tags=["用户管理"], description="获取用户列表")
sys_router.add_api_route('/users/{user_id}', user_get, methods=["GET"], tags=["用户管理"], description="获取用户详情")
sys_router.add_api_route('/users/{user_id}', user_update, methods=["PUT"], tags=["用户管理"], description="更新用户")
sys_router.add_api_route('/users/{user_id}', user_delete, methods=["DELETE"], tags=["用户管理"], description="删除用户")

sys_router.add_api_route('/departments', dept_create, methods=["POST"], tags=["部门管理"], description="创建部门")
sys_router.add_api_route('/departments', dept_list, methods=["GET"], tags=["部门管理"], description="获取部门列表")
sys_router.add_api_route('/departments/tree', dept_tree, methods=["GET"], tags=["部门管理"], description="获取部门树")
sys_router.add_api_route('/departments/{dept_id}', dept_get, methods=["GET"], tags=["部门管理"], description="获取部门详情")
sys_router.add_api_route('/departments/{dept_id}', dept_update, methods=["PUT"], tags=["部门管理"], description="更新部门")
sys_router.add_api_route('/departments/{dept_id}', dept_delete, methods=["DELETE"], tags=["部门管理"], description="删除部门")

sys_router.add_api_route('/roles', role_create, methods=["POST"], tags=["角色管理"], description="创建角色")
sys_router.add_api_route('/roles', role_list, methods=["GET"], tags=["角色管理"], description="获取角色列表")
sys_router.add_api_route('/roles/{role_id}', role_get, methods=["GET"], tags=["角色管理"], description="获取角色详情")
sys_router.add_api_route('/roles/{role_id}', role_update, methods=["PUT"], tags=["角色管理"], description="更新角色")
sys_router.add_api_route('/roles/{role_id}', role_delete, methods=["DELETE"], tags=["角色管理"], description="删除角色")
sys_router.add_api_route('/roles/{role_id}/permissions', role_get_perms, methods=["GET"], tags=["角色管理"], description="获取角色权限")
sys_router.add_api_route('/roles/{role_id}/permissions', role_set_perms, methods=["PUT"], tags=["角色管理"], description="设置角色权限")

sys_router.add_api_route('/permissions', perm_create, methods=["POST"], tags=["权限管理"], description="创建权限")
sys_router.add_api_route('/permissions', perm_list, methods=["GET"], tags=["权限管理"], description="获取权限列表")
sys_router.add_api_route('/permissions/menus', perm_user_menus, methods=["GET"], tags=["权限管理"], description="获取当前用户菜单")
sys_router.add_api_route('/permissions/init', perm_init, methods=["POST"], tags=["权限管理"], description="初始化默认权限")
sys_router.add_api_route('/permissions/{perm_id}', perm_get, methods=["GET"], tags=["权限管理"], description="获取权限详情")
sys_router.add_api_route('/permissions/{perm_id}', perm_update, methods=["PUT"], tags=["权限管理"], description="更新权限")
sys_router.add_api_route('/permissions/{perm_id}', perm_delete, methods=["DELETE"], tags=["权限管理"], description="删除权限")

# 模型管理API路由
sys_router.add_api_route('/models', model_create, methods=["POST"], tags=["模型管理"], description="创建模型")
sys_router.add_api_route('/models', model_list, methods=["GET"], tags=["模型管理"], description="获取模型列表")
sys_router.add_api_route('/models/active', model_active_list, methods=["GET"], tags=["模型管理"], description="获取可用模型列表")
sys_router.add_api_route('/models/{model_id}', model_get, methods=["GET"], tags=["模型管理"], description="获取模型详情")
sys_router.add_api_route('/models/{model_id}', model_update, methods=["PUT"], tags=["模型管理"], description="更新模型")
sys_router.add_api_route('/models/{model_id}', model_delete, methods=["DELETE"], tags=["模型管理"], description="删除模型")
sys_router.add_api_route('/models/{model_id}/test', model_test, methods=["POST"], tags=["模型管理"], description="测试模型连接")

# MCP管理API路由
sys_router.add_api_route('/mcps', mcp_create, methods=["POST"], tags=["MCP管理"], description="创建MCP服务")
sys_router.add_api_route('/mcps', mcp_list, methods=["GET"], tags=["MCP管理"], description="获取MCP服务列表")
sys_router.add_api_route('/mcps/{mcp_id}', mcp_get, methods=["GET"], tags=["MCP管理"], description="获取MCP服务详情")
sys_router.add_api_route('/mcps/{mcp_id}', mcp_update, methods=["PUT"], tags=["MCP管理"], description="更新MCP服务")
sys_router.add_api_route('/mcps/{mcp_id}', mcp_delete, methods=["DELETE"], tags=["MCP管理"], description="删除MCP服务")
sys_router.add_api_route('/mcps/{mcp_id}/sync', mcp_sync, methods=["POST"], tags=["MCP管理"], description="同步MCP工具信息")
sys_router.add_api_route('/mcps/{mcp_id}/tools', mcp_tools_list, methods=["GET"], tags=["MCP管理"], description="获取MCP工具列表")
sys_router.add_api_route('/mcps/{mcp_id}/tools/{tool_name}/invoke', mcp_tool_invoke, methods=["POST"], tags=["MCP管理"], description="调用MCP工具")
sys_router.add_api_route('/mcps/tools/all', mcp_all_tools, methods=["GET"], tags=["MCP管理"], description="获取所有MCP工具列表")

# 仪表盘API路由
sys_router.add_api_route('/dashboard/overview', dashboard_overview, methods=["GET"], tags=["仪表盘"], description="获取仪表盘概览数据")
sys_router.add_api_route('/dashboard/full', dashboard_full, methods=["GET"], tags=["仪表盘"], description="获取完整仪表盘数据")
sys_router.add_api_route('/dashboard/complete', dashboard_complete, methods=["GET"], tags=["仪表盘"], description="获取完整仪表盘数据（含排行榜和趋势）")
sys_router.add_api_route('/dashboard/agents', dashboard_agent_stats, methods=["GET"], tags=["仪表盘"], description="获取Agent统计数据")
sys_router.add_api_route('/dashboard/skills', dashboard_skill_stats, methods=["GET"], tags=["仪表盘"], description="获取Skill统计数据")
sys_router.add_api_route('/dashboard/mcps', dashboard_mcp_stats, methods=["GET"], tags=["仪表盘"], description="获取MCP统计数据")
sys_router.add_api_route('/dashboard/chats', dashboard_chat_stats, methods=["GET"], tags=["仪表盘"], description="获取对话统计数据")
sys_router.add_api_route('/dashboard/activities', dashboard_activities, methods=["GET"], tags=["仪表盘"], description="获取最近活动记录")
sys_router.add_api_route('/dashboard/popular', dashboard_popular, methods=["GET"], tags=["仪表盘"], description="获取热门排行榜数据")
sys_router.add_api_route('/dashboard/daily-trend', dashboard_daily_trend, methods=["GET"], tags=["仪表盘"], description="获取按天趋势数据")

# 提示词管理API路由
sys_router.add_api_route('/prompts', prompt_create, methods=["POST"], tags=["提示词管理"], description="创建提示词")
sys_router.add_api_route('/prompts', prompt_list, methods=["GET"], tags=["提示词管理"], description="获取提示词列表")
sys_router.add_api_route('/prompts/{prompt_id}', prompt_get, methods=["GET"], tags=["提示词管理"], description="获取提示词详情")
sys_router.add_api_route('/prompts/{prompt_id}', prompt_update, methods=["PUT"], tags=["提示词管理"], description="更新提示词")
sys_router.add_api_route('/prompts/{prompt_id}', prompt_delete, methods=["DELETE"], tags=["提示词管理"], description="删除提示词")

# 知识库管理API路由
sys_router.add_api_route('/knowledge-bases', kb_create, methods=["POST"], tags=["知识库管理"], description="创建知识库")
sys_router.add_api_route('/knowledge-bases', kb_list, methods=["GET"], tags=["知识库管理"], description="获取知识库列表")
sys_router.add_api_route('/knowledge-bases/{kb_id}', kb_get, methods=["GET"], tags=["知识库管理"], description="获取知识库详情")
sys_router.add_api_route('/knowledge-bases/{kb_id}', kb_update, methods=["PUT"], tags=["知识库管理"], description="更新知识库")
sys_router.add_api_route('/knowledge-bases/{kb_id}', kb_delete, methods=["DELETE"], tags=["知识库管理"], description="删除知识库")
sys_router.add_api_route('/knowledge-bases/{kb_id}/documents', doc_list, methods=["GET"], tags=["知识库管理"], description="获取文档列表")
sys_router.add_api_route('/knowledge-bases/documents', doc_create, methods=["POST"], tags=["知识库管理"], description="创建文档")
sys_router.add_api_route('/knowledge-bases/documents/{doc_id}', doc_delete, methods=["DELETE"], tags=["知识库管理"], description="删除文档")
sys_router.add_api_route('/knowledge-bases/doc2db',docs2_milvusdb,methods=["POST"],tags=['知识库管理'],description='文档向量化入库')

