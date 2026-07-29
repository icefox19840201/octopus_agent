import json
import asyncio
import uuid
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from pydantic import create_model, BaseModel
from dataaccess.database import SessionLocal
from dataaccess.agent_repo import AgentRepo, AgentSkillMappingRepo, AgentToolMappingRepo, MCPToolRepo, LLMModelRepo
from dataaccess.skill_repo import SkillRepo
from dataaccess.chat_repo import ChatRepo
from dataaccess.role_repo import UserRoleRepo
from settings import redis_uri
from biziness.skill_service import SkillService
from utils.pagination import PageResult, paginate
from utils.logger import logger
from langchain_core.tools import StructuredTool
from .llm import get_deepagent_response_with_stream,get_deepagent_response_sync,get_deepagent_response_with_stream_async
from langchain_mcp_adapters.client import MultiServerMCPClient
from dataaccess.mcp_repo import MCPRepo
from dataaccess.agent_repo import AgentRepo as RawAgentRepo
from langgraph.checkpoint.redis import RedisSaver, AsyncRedisSaver

_checkpointer = None
_async_checkpointer = None

def _init_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        try:
            _checkpointer = RedisSaver(redis_uri)
            _checkpointer.setup()
            logger.info("RedisSaver 初始化成功")
        except Exception as e:
            logger.exception(f"RedisSaver 初始化失败: {e}")
            _checkpointer = None


async def _init_async_checkpointer():
    global _async_checkpointer
    if _async_checkpointer is None:
        try:
            _async_checkpointer = AsyncRedisSaver(redis_uri)
            await _async_checkpointer.setup()
            logger.info("AsyncRedisSaver 初始化成功")
        except Exception as e:
            logger.exception(f"AsyncRedisSaver 初始化失败: {e}")
            _async_checkpointer = None


class AgentService:
    """Agent业务逻辑服务类"""

    AGENT_CONFIG_DIR = Path(__file__).parent.parent / "config" / "agent_config"

    @staticmethod
    def _get_session() -> Session:
        return SessionLocal()

    @staticmethod
    def save_agent_config(agent_id: str, agent_data: Dict[str, Any], user_id: str = None, department_id: str = None) -> bool:
        try:
            db = AgentService._get_session()
            try:
                agent_dict = {
                    "agent_id": agent_id,
                    "name": agent_data.get("name", ""),
                    "description": agent_data.get("description", ""),
                    "status": 1 if agent_data.get("status", "active") == "active" else 0,
                    "type": agent_data.get("agent_space", "private"),
                    "model_id": agent_data.get("model_id"),
                    "prompt_id": agent_data.get("prompt_id"),
                    "temperature": agent_data.get("temperature", 0.7),
                    "top_p": agent_data.get("top_p", 0.9),
                    "enable_memory": agent_data.get("enable_memory", True),
                    "is_locked": agent_data.get("is_locked", False),
                    "created_by": user_id,
                    "department_id": department_id
                }
                agent = AgentRepo.create(db, agent_dict)

                # 权限通过AgentModel的created_by和type字段控制
                # - type="private": 仅创建者可见（通过created_by判断）
                # - type="group": 同部门可见（需要结合部门信息判断）
                # - type="public": 所有人可见

                skill_ids = agent_data.get("skills", [])
                if skill_ids:
                    AgentSkillMappingRepo.set_agent_skills(db, agent_id, skill_ids)

                # 保存工具关联
                tool_ids = agent_data.get("tools", [])
                if tool_ids:
                    AgentToolMappingRepo.set_agent_tools(db, agent_id, tool_ids)

                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"保存Agent失败: {e}")
            logger.exception(e)
            return False

    @staticmethod
    def get_agent_config(agent_id: str) -> Optional[Dict[str, Any]]:
        try:
            db = AgentService._get_session()
            try:
                agent = AgentRepo.get_by_id(db, agent_id)
                if not agent:
                    return None

                mappings = AgentSkillMappingRepo.get_by_agent(db, agent.agent_id)
                skill_ids = [m.skills_id for m in mappings if m.skills_id]
                
                # 获取技能名称映射
                skill_names = {}
                for skill_id in skill_ids:
                    skill = SkillRepo.get_by_id(db, skill_id)
                    if skill:
                        skill_names[skill_id] = skill.skills_name or skill_id
                    else:
                        skill_names[skill_id] = skill_id

                # 获取工具关联
                tool_mappings = AgentToolMappingRepo.get_by_agent(db, agent.agent_id)
                tool_ids = [m.tool_id for m in tool_mappings if m.tool_id]
                
                # 获取工具详情和名称映射
                tools = []
                tool_names = {}
                for tool_id in tool_ids:
                    tool = MCPToolRepo.get_by_id(db, tool_id)
                    if tool:
                        tools.append({
                            "id": tool.id,
                            "name": tool.name,
                            "description": tool.description or ""
                        })
                        tool_names[tool_id] = tool.name

                # 获取模型信息
                model_info = None
                if agent.model_id:
                    model = LLMModelRepo.get_by_id(db, agent.model_id)
                    if model:
                        model_info = {
                            "id": model.id,
                            "name": model.name,
                            "model_name": model.model_name,
                            "provider": model.provider
                        }

                # 获取提示词信息
                prompt_info = None
                if agent.prompt_id:
                    from dataaccess.prompt_repo import PromptRepo
                    prompt = PromptRepo.get_by_id(db, agent.prompt_id)
                    if prompt:
                        prompt_info = {
                            "id": prompt.id,
                            "name": prompt.name,
                            "content": prompt.content
                        }

                return {
                    "id": agent.agent_id,
                    "name": agent.name,
                    "description": agent.description or "",
                    "skills": skill_ids,
                    "skill_names": skill_names,
                    "tools": tool_ids,
                    "tool_names": tool_names,
                    "tool_details": tools,
                    "model_id": agent.model_id,
                    "model": model_info,
                    "prompt_id": agent.prompt_id,
                    "prompt": prompt_info,
                    "status": "active" if agent.status == 1 else "error",
                    "config": {},
                    "agent_space": agent.type or "private",
                    "created_by": agent.created_by,
                    "is_locked": agent.is_locked if agent.is_locked is not None else False,
                    "temperature": agent.temperature if agent.temperature is not None else 0.7,
                    "top_p": agent.top_p if agent.top_p is not None else 0.9,
                    "enable_memory": agent.enable_memory if agent.enable_memory is not None else True,
                    "createdAt": agent.created_at.isoformat() if agent.created_at else "",
                    "updatedAt": agent.updated_at.isoformat() if agent.updated_at else ""
                }
            finally:
                db.close()
        except Exception as e:
            logger.error(f"读取Agent失败: {e}")
            logger.exception(e)
            return None

    @staticmethod
    def delete_agent_config(agent_id: str, user_id: str = None) -> Dict[str, Any]:
        """删除Agent配置"""
        try:
            db = AgentService._get_session()
            try:
                agent = AgentRepo.get_by_id(db, agent_id)
                if not agent:
                    return {"success": False, "message": "Agent不存在"}

                # 权限检查：只有创建者或管理员可以删除
                if user_id:
                    is_admin = UserRoleRepo.is_user_admin(db, user_id)
                    if agent.created_by != user_id and not is_admin:
                        return {"success": False, "message": "无权删除，仅本人或管理员可以删除"}

                AgentSkillMappingRepo.delete_by_agent(db, agent_id)
                success = AgentRepo.delete(db, agent_id)
                return {"success": success}
            finally:
                db.close()
        except Exception as e:
            logger.error(f"删除Agent失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}

    @staticmethod
    def list_all_agents(user_id: str = None, department_id: str = None) -> List[Dict[str, Any]]:
        """获取Agent列表（带空间过滤）"""
        try:
            db = AgentService._get_session()
            try:
                if user_id:
                    agents = AgentRepo.get_visible_agents(db, user_id, department_id)
                else:
                    agents = AgentRepo.get_all(db)
                result = []
                for agent in agents:
                    mappings = AgentSkillMappingRepo.get_by_agent(db, agent.agent_id)
                    skill_ids = [m.skills_id for m in mappings if m.skills_id]
                    
                    # 获取工具关联
                    tool_mappings = AgentToolMappingRepo.get_by_agent(db, agent.agent_id)
                    tool_ids = [m.tool_id for m in tool_mappings if m.tool_id]
                    
                    config = {}
                    if agent.config:
                        try:
                            config = json.loads(agent.config)
                        except json.JSONDecodeError:
                            config = {}
                    result.append({
                        "id": agent.agent_id,
                        "name": agent.name,
                        "description": agent.description or "",
                        "skills": skill_ids,
                        "tools": tool_ids,
                        "model_id": agent.model_id,
                        "status": "active" if agent.status == 1 else "error",
                        "config": config,
                        "agent_space": agent.type or "private",
                        "created_by": agent.created_by,
                        "temperature": agent.temperature if agent.temperature is not None else 0.7,
                        "top_p": agent.top_p if agent.top_p is not None else 0.9,
                        "enable_memory": agent.enable_memory if agent.enable_memory is not None else True,
                        "createdAt": agent.created_at.isoformat() if agent.created_at else "",
                        "updatedAt": agent.updated_at.isoformat() if agent.updated_at else ""
                    })
                return result
            finally:
                db.close()
        except Exception as e:
            logger.error(f"获取Agent列表失败: {e}")
            logger.exception(e)
            return []

    @staticmethod
    def paginate_agents(page: int = 1, page_size: int = 10, user_id: str = None, department_id: str = None) -> dict:
        """分页获取Agent列表（带空间过滤）"""
        try:
            db = AgentService._get_session()
            try:
                offset, limit = paginate(page, page_size)
                if user_id:
                    total = AgentRepo.count_visible_agents(db, user_id, department_id)
                    agents = AgentRepo.get_visible_agents_paginated(db, user_id, department_id, offset, limit)
                else:
                    total = AgentRepo.count_all(db)
                    agents = AgentRepo.get_all_paginated(db, offset, limit)
                items = []
                for agent in agents:
                    mappings = AgentSkillMappingRepo.get_by_agent(db, agent.agent_id)
                    skill_ids = [m.skills_id for m in mappings if m.skills_id]
                    
                    # 获取技能名称映射
                    skill_names = {}
                    for skill_id in skill_ids:
                        skill = SkillRepo.get_by_id(db, skill_id)
                        if skill:
                            skill_names[skill_id] = skill.skills_name or skill_id
                        else:
                            skill_names[skill_id] = skill_id
                    
                    # 获取工具关联
                    tool_mappings = AgentToolMappingRepo.get_by_agent(db, agent.agent_id)
                    tool_ids = [m.tool_id for m in tool_mappings if m.tool_id]
                    
                    # 获取工具名称映射
                    tool_names = {}
                    for tool_id in tool_ids:
                        tool = MCPToolRepo.get_by_id(db, tool_id)
                        if tool:
                            tool_names[tool_id] = tool.name
                    
                    config = {}
                    if agent.config:
                        try:
                            config = json.loads(agent.config)
                        except json.JSONDecodeError:
                            config = {}
                    # 获取提示词名称
                    prompt_name = None
                    if agent.prompt_id:
                        from dataaccess.prompt_repo import PromptRepo
                        prompt = PromptRepo.get_by_id(db, agent.prompt_id)
                        if prompt:
                            prompt_name = prompt.name

                    items.append({
                        "id": agent.agent_id,
                        "name": agent.name,
                        "description": agent.description or "",
                        "skills": skill_ids,
                        "skill_names": skill_names,
                        "tools": tool_ids,
                        "tool_names": tool_names,
                        "model_id": agent.model_id,
                        "prompt_id": agent.prompt_id,
                        "prompt_name": prompt_name,
                        "status": "active" if agent.status == 1 else "error",
                        "config": config,
                        "agent_space": agent.type or "private",
                        "created_by": agent.created_by,
                        "is_locked": agent.is_locked if agent.is_locked is not None else False,
                        "temperature": agent.temperature if agent.temperature is not None else 0.7,
                        "top_p": agent.top_p if agent.top_p is not None else 0.9,
                        "enable_memory": agent.enable_memory if agent.enable_memory is not None else True,
                        "createdAt": agent.created_at.isoformat() if agent.created_at else "",
                        "updatedAt": agent.updated_at.isoformat() if agent.updated_at else ""
                    })
                return PageResult(items, total, page, limit).to_dict()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"分页获取Agent列表失败: {e}")
            logger.exception(e)
            return PageResult([], 0, page, page_size).to_dict()

    @staticmethod
    def search_agents(page: int = 1, page_size: int = 10, user_id: str = None, department_id: str = None, keyword: str = None) -> dict:
        """搜索Agent列表（分页，带空间过滤）"""
        try:
            db = AgentService._get_session()
            try:
                offset, limit = paginate(page, page_size)
                if user_id:
                    total = AgentRepo.count_search_visible_agents(db, user_id, department_id, keyword)
                    agents = AgentRepo.search_visible_agents_paginated(db, user_id, department_id, keyword, offset, limit)
                else:
                    # 未登录用户只能看到公开的Agent，且不能搜索（或搜索公开的）
                    total = RawAgentRepo.count_all(db)
                    agents = RawAgentRepo.get_all_paginated(db, offset, limit)

                items = []
                for agent in agents:
                    # 获取技能关联
                    mappings = AgentSkillMappingRepo.get_by_agent(db, agent.agent_id)
                    skill_ids = [m.skills_id for m in mappings if m.skills_id]

                    # 获取技能名称映射
                    skill_names = {}
                    for skill_id in skill_ids:
                        skill = SkillRepo.get_by_id(db, skill_id)
                        if skill:
                            skill_names[skill_id] = skill.skills_name or skill_id
                        else:
                            skill_names[skill_id] = skill_id

                    # 获取工具关联
                    tool_mappings = AgentToolMappingRepo.get_by_agent(db, agent.agent_id)
                    tool_ids = [m.tool_id for m in tool_mappings if m.tool_id]

                    # 获取工具名称映射
                    tool_names = {}
                    for tool_id in tool_ids:
                        tool = MCPToolRepo.get_by_id(db, tool_id)
                        if tool:
                            tool_names[tool_id] = tool.name

                    config = {}
                    if agent.config:
                        try:
                            config = json.loads(agent.config)
                        except json.JSONDecodeError:
                            config = {}
                    
                    # 获取提示词名称
                    prompt_name = None
                    if agent.prompt_id:
                        from dataaccess.prompt_repo import PromptRepo
                        prompt = PromptRepo.get_by_id(db, agent.prompt_id)
                        if prompt:
                            prompt_name = prompt.name
                    
                    items.append({
                        "id": agent.agent_id,
                        "name": agent.name,
                        "description": agent.description or "",
                        "skills": skill_ids,
                        "skill_names": skill_names,
                        "tools": tool_ids,
                        "tool_names": tool_names,
                        "model_id": agent.model_id,
                        "prompt_id": agent.prompt_id,
                        "prompt_name": prompt_name,
                        "status": "active" if agent.status == 1 else "error",
                        "config": config,
                        "agent_space": agent.type or "private",
                        "created_by": agent.created_by,
                        "is_locked": agent.is_locked if agent.is_locked is not None else False,
                        "temperature": agent.temperature if agent.temperature is not None else 0.7,
                        "top_p": agent.top_p if agent.top_p is not None else 0.9,
                        "enable_memory": agent.enable_memory if agent.enable_memory is not None else True,
                        "createdAt": agent.created_at.isoformat() if agent.created_at else "",
                        "updatedAt": agent.updated_at.isoformat() if agent.updated_at else ""
                    })
                return PageResult(items, total, page, limit).to_dict()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"搜索Agent列表失败: {e}")
            logger.exception(e)
            return PageResult([], 0, page, page_size).to_dict()

    @staticmethod
    def update_agent_config(agent_id: str, update_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        try:
            db = AgentService._get_session()
            try:
                # 先获取当前Agent信息
                existing_agent = AgentRepo.get_by_id(db, agent_id)
                if not existing_agent:
                    return {"success": False, "message": "Agent不存在"}
                
                # 权限检查：只有创建者或管理员可以修改
                if user_id:
                    is_admin = UserRoleRepo.is_user_admin(db, user_id)
                    if existing_agent.created_by != user_id and not is_admin:
                        return {"success": False, "message": "无权修改，仅本人或管理员可以修改"}

                # 检查锁定状态：如果已锁定且当前用户不是创建者，则拒绝修改
                if existing_agent.is_locked and user_id and existing_agent.created_by != user_id:
                    logger.warning(f"Agent已被锁定，仅创建者可修改: agent_id={agent_id}, created_by={existing_agent.created_by}, current_user={user_id}")
                    raise PermissionError("该智能体已被锁定，仅创建者可以修改配置")

                update_dict = {}
                if "name" in update_data:
                    update_dict["name"] = update_data["name"]
                if "description" in update_data:
                    update_dict["description"] = update_data["description"]
                if "status" in update_data:
                    update_dict["status"] = 1 if update_data["status"] == "active" else 0
                if "config" in update_data:
                    config = update_data["config"]
                    if not isinstance(config, str):
                        config = json.dumps(config, ensure_ascii=False)
                    update_dict["config"] = config
                # 模型参数
                if "temperature" in update_data:
                    update_dict["temperature"] = float(update_data["temperature"])
                if "top_p" in update_data:
                    update_dict["top_p"] = float(update_data["top_p"])
                if "enable_memory" in update_data:
                    update_dict["enable_memory"] = bool(update_data["enable_memory"])
                # 锁定状态
                if "is_locked" in update_data:
                    update_dict["is_locked"] = bool(update_data["is_locked"])
                # 可见范围
                if "agent_space" in update_data:
                    update_dict["type"] = update_data["agent_space"]

                if update_dict:
                    agent = AgentRepo.update(db, agent_id, update_dict)
                    if not agent:
                        return False

                if "skills" in update_data:
                    AgentSkillMappingRepo.set_agent_skills(db, agent_id, update_data["skills"])

                # 更新工具关联
                if "tools" in update_data:
                    AgentToolMappingRepo.set_agent_tools(db, agent_id, update_data["tools"])

                # 更新模型ID（空字符串转为None）
                if "model_id" in update_data:
                    model_id = update_data["model_id"]
                    if model_id == '' or model_id is None:
                        model_id = None
                    AgentRepo.update(db, agent_id, {"model_id": model_id})

                # 更新提示词ID（空字符串转为None）
                if "prompt_id" in update_data:
                    prompt_id = update_data["prompt_id"]
                    if prompt_id == '' or prompt_id is None:
                        prompt_id = None
                    AgentRepo.update(db, agent_id, {"prompt_id": prompt_id})

                return {"success": True}
            finally:
                db.close()
        except PermissionError:
            raise
        except Exception as e:
            logger.error(f"更新Agent失败: {e}")
            logger.exception(e)
            return {"success": False, "message": f"更新失败: {str(e)}"}
    @staticmethod
    def chat(skill_sources, filesystem_backend, content, conversation, agent_id=None):
        """
        智能体聊天（同步非流式）
        """
        _init_checkpointer()
        checkpointer = _checkpointer
        
        # 获取智能体的提示词内容
        system_prompt = None
        if agent_id:
            agent_data = AgentService.get_agent_config(agent_id)
            if agent_data:
                prompt_info = agent_data.get("prompt")
                if prompt_info and prompt_info.get("content"):
                    system_prompt = prompt_info.get("content")
                    logger.info(f"从Agent配置获取提示词: {prompt_info.get('name', '未命名')}")

        
        return get_deepagent_response_sync(
            skill_sources=skill_sources,
            filesystem_backend=filesystem_backend,
            checkpointer=checkpointer,
            conversation=conversation,
            content=content,
            system_prompt=system_prompt
        )

    @staticmethod
    def _rebuild_tool_args_schema(tool):
        """将工具 args_schema 从 dict 转换为 Pydantic BaseModel 类型
        langchain_mcp_adapters 返回的工具 args_schema 是原始 dict，
        需要转为 Pydantic 模型才能被 create_deep_agent 正确绑定。
        """
        schema_dict = getattr(tool, 'args_schema', None)
        if schema_dict is None or not isinstance(schema_dict, dict):
            return tool
        
        properties = schema_dict.get('properties', {})
        required = schema_dict.get('required', [])
        
        fields = {}
        for param_name, param_info in properties.items():
            param_type = param_info.get('type', 'string') if isinstance(param_info, dict) else 'string'
            type_map = {'string': str, 'integer': int, 'number': float, 'boolean': bool}
            field_type = type_map.get(param_type, str)
            fields[param_name] = (field_type, ... if param_name in required else None)
        
        ArgsModel = create_model(f'{tool.name}Args', **fields) if fields else create_model(f'{tool.name}Args', __base__=BaseModel)
        
        # langchain_mcp_adapters 只设置了 coroutine，没有设置 func
        # langgraph ToolNode._execute_tool_sync 走的是同步 tool.invoke() → _run() 路径
        # 所以需要补充同步 func，用 asyncio.run() 包装 coroutine
        func = tool.func
        original_coroutine = tool.coroutine
        if original_coroutine is not None:
            async def _clean_coroutine(**kwargs):
                raw = await original_coroutine(**kwargs)
                return AgentService._extract_tool_text(raw)
            coroutine = _clean_coroutine
            func = lambda **kwargs: asyncio.run(coroutine(**kwargs))
        else:
            coroutine = None
        
        new_tool = StructuredTool(
            name=tool.name,
            description=tool.description,
            args_schema=ArgsModel,
            func=func,
            coroutine=coroutine
        )
        return new_tool

    @staticmethod
    def _extract_tool_text(raw_result):
        """从 MCP content_and_artifact 格式中提取纯文本"""
        content = raw_result
        if isinstance(raw_result, tuple):
            content = raw_result[0]
        if isinstance(content, list):
            texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            if texts:
                return "\n".join(texts)
            return str(content)
        return str(content)

    @staticmethod
    async def _load_mcp_tools_from_mcp(mcp_tool_groups: Dict[str, List[str]]):
        """使用 langchain_mcp_adapters 从 MCP 服务器异步加载真实 LangChain BaseTool 对象
        
        Args:
            mcp_tool_groups: {mcp_id: [tool_name1, tool_name2, ...]}
            
        Returns:
            过滤后的 LangChain BaseTool 列表
        """
        if not mcp_tool_groups:
            return []
        
        db = AgentService._get_session()
        try:
            all_tools = []
            
            async def _load_single_mcp(mcp_id, configured_names):
                mcp = MCPRepo.get_by_id(db, mcp_id)
                if not mcp:
                    logger.warning(f"MCP服务不存在: {mcp_id}")
                    return []
                
                server_name = mcp.name or f"mcp_{mcp_id}"
                if mcp.type == 'sse':
                    connection_config = {server_name: {"transport": "sse", "url": mcp.endpoint}}
                elif mcp.type == 'streamable-http':
                    connection_config = {server_name: {"transport": "http", "url": mcp.endpoint}}
                else:
                    logger.warning(f"不支持的MCP类型: {mcp.type}")
                    return []
                
                logger.info(f"正在从MCP {mcp.name} ({mcp.endpoint}) 获取工具")
                try:
                    client = MultiServerMCPClient(connection_config)
                    mcp_tools = await client.get_tools()
                except Exception as e:
                    logger.error(f"从MCP {mcp.name} ({mcp.endpoint}) 获取工具失败: {e}")
                    return []
                
                configured_set = set(configured_names)
                filtered = []
                for t in mcp_tools:
                    t_name = getattr(t, 'name', '')
                    if t_name in configured_set:
                        rebuilt = AgentService._rebuild_tool_args_schema(t)
                        filtered.append(rebuilt)
                        logger.info(f"从MCP {mcp.name} 加载工具: {t_name}")
                
                return filtered
            
            tasks = [_load_single_mcp(mcp_id, names) for mcp_id, names in mcp_tool_groups.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"加载MCP工具时发生异常: {result}")
                    continue
                all_tools.extend(result)
            
            return all_tools
        finally:
            db.close()

    @staticmethod
    def _load_mcp_tools_sync(mcp_tool_groups: Dict[str, List[str]]):
        """同步包装器：兼容有无运行中事件循环两种情况"""
        try:
            loop = asyncio.get_running_loop()
            # 已有运行中的事件循环，在新线程中用独立事件循环执行

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(AgentService._load_mcp_tools_from_mcp(mcp_tool_groups))
                )
                return future.result()
        except RuntimeError:
            # 没有运行中的事件循环，直接使用 asyncio.run
            return asyncio.run(AgentService._load_mcp_tools_from_mcp(mcp_tool_groups))

    @staticmethod
    def chat_stream(skill_sources, filesystem_backend, content, conversation, agent_id=None, user_id=None, tool_ids=None, model_id=None, uploaded_files=None):
        """
        智能体聊天（流式）
        返回 SSE 格式的生成器
        
        Args:
            uploaded_files: 上传的文件列表，每个文件包含 name, path, size
        """
        uploaded_files = uploaded_files or []
        
        # 获取agent配置
        agent_config = {}
        agent_data = None
        if agent_id:
            agent_data = AgentService.get_agent_config(agent_id)
            if agent_data:
                agent_config = agent_data.get("config", {})

        # 从配置中获取模型参数
        temperature = agent_config.get("temperature", 0.7)
        top_p = agent_config.get("top_p", 0.9)
        # enable_memory 直接存储在 agent_data 根级别，不在 config 中
        enable_memory = agent_data.get("enable_memory", True) if agent_data else True
        logger.info(f"记忆功能配置: enable_memory={enable_memory}, agent_id={agent_id}")
        
        # 如果没有传入model_id，从agent配置中获取
        if model_id is None and agent_data:
            model_id = agent_data.get("model_id")
            logger.info(f"从Agent配置获取模型ID: {model_id}")
        
        # 获取智能体的提示词内容
        system_prompt = None
        if agent_data:
            prompt_info = agent_data.get("prompt")
            if prompt_info and prompt_info.get("content"):
                system_prompt = prompt_info.get("content")
                logger.info(f"从Agent配置获取提示词: {prompt_info.get('name', '未命名')}")

        _init_checkpointer()
        checkpointer = _checkpointer if enable_memory else None
        
        if enable_memory:
            logger.info(f"记忆功能已启用，使用 Redis checkpoint: conversation={conversation}")
        else:
            logger.info(f"记忆功能已禁用，不使用 checkpoint: conversation={conversation}")

        # 使用 langchain_mcp_adapters 从 MCP 服务器获取真实工具列表
        tools = []
        logger.info(f"工具ID列表: {tool_ids}")
        if tool_ids:
            db = AgentService._get_session()
            try:
                # 按 mcp_id 分组工具名称
                mcp_tool_groups = {}
                for tool_id in tool_ids:
                    tool = MCPToolRepo.get_by_id(db, tool_id)
                    if tool:
                        mcp_id = tool.mcp_id
                        if mcp_id not in mcp_tool_groups:
                            mcp_tool_groups[mcp_id] = []
                        mcp_tool_groups[mcp_id].append(tool.name)
                
                if mcp_tool_groups:
                    logger.info(f"按MCP分组: {mcp_tool_groups}")
                    tools = AgentService._load_mcp_tools_sync(mcp_tool_groups)
                    logger.info(f"从MCP加载了 {len(tools)} 个工具")
            finally:
                db.close()
        
        ai_response_parts = []

        # 流式输出并收集响应
        logger.info(f"调用 get_deepagent_response_with_stream，tools: {tools}, enable_memory={enable_memory}")
        try:
            for data in get_deepagent_response_with_stream(
                skill_sources=skill_sources,
                filesystem_backend=filesystem_backend,
                checkpointer=checkpointer,
                conversation=conversation,
                content=content,
                temperature=temperature,
                top_p=top_p,
                tools=tools,
                model_id=model_id,
                use_memory=enable_memory,
                system_prompt=system_prompt
            ):
                yield data
                # 收集token用于保存到数据库
                try:
                    parsed = json.loads(data.replace('data: ', ''))
                    if parsed.get('type') == 'token':
                        ai_response_parts.append(parsed.get('content', ''))
                except:
                    pass
        except asyncio.CancelledError:
            logger.info(f"聊天流被用户终止: conversation={conversation}")
            raise
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"聊天流错误: {error_msg}")

            # 检查是否是 LangGraph Redis 序列化器错误
            if "_encode_constructor_args" in error_msg or "JsonPlusRedisSerializer" in error_msg:
                logger.error(f"AgentService 捕获到 LangGraph Redis 序列化器错误: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'content': '会话存储出现兼容性问题，请使用新的会话 ID 重试'}, ensure_ascii=False)}\n\n"
                return

            # 检查是否是 DeepSeek 推理模式错误
            if "reasoning_content" in error_msg or "thinking mode" in error_msg:
                logger.error(f"AgentService 捕获到 DeepSeek 推理模式错误: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'content': '当前模型启用了推理模式，但会话不支持推理内容传递。请使用新的会话 ID 重试。'}, ensure_ascii=False)}\n\n"
                return

            # 其他错误重新抛出
            raise

        # 保存对话记录到数据库
        logger.info(f"准备保存对话记录: agent_id={agent_id}, user_id={user_id}, ai_response长度={len(ai_response_parts)}")
        if agent_id and user_id:
            try:
                db = SessionLocal()
                ai_message = "".join(ai_response_parts)
                logger.info(f"保存对话记录: agent_id={agent_id}, user_id={user_id}, conversation={conversation}")
                result = ChatRepo.create(db, {
                    "agent_id": agent_id,
                    "user_id": user_id,
                    "user_message": content,
                    "ai_message": ai_message,
                    "conversation_id": conversation
                })
                logger.info(f"对话记录保存成功: id={result.id}")
                db.close()
            except Exception as e:
                logger.exception(f"保存对话记录失败: {e}")
        else:
            logger.warning(f"无法保存对话记录: agent_id={agent_id}, user_id={user_id}, 参数缺失")

    @staticmethod
    async def chat_stream_async(skill_sources, filesystem_backend, content, conversation, agent_id=None, user_id=None, tool_ids=None, model_id=None, uploaded_files=None):
        """
        智能体聊天（异步流式）
        返回 SSE 格式的异步生成器
        
        Args:
            uploaded_files: 上传的文件列表，每个文件包含 name, path, size
        """
        uploaded_files = uploaded_files or []
        
        # 获取agent配置
        agent_config = {}
        agent_data = None
        if agent_id:
            agent_data = AgentService.get_agent_config(agent_id)
            if agent_data:
                agent_config = agent_data.get("config", {})

        # 从配置中获取模型参数
        temperature = agent_config.get("temperature", 0.7)
        top_p = agent_config.get("top_p", 0.9)
        # enable_memory 直接存储在 agent_data 根级别，不在 config 中
        enable_memory = agent_data.get("enable_memory", True) if agent_data else True
        logger.info(f"记忆功能配置: enable_memory={enable_memory}, agent_id={agent_id}")
        
        # 如果没有传入model_id，从agent配置中获取
        if model_id is None and agent_data:
            model_id = agent_data.get("model_id")
            logger.info(f"从Agent配置获取模型ID: {model_id}")
        
        # 获取智能体的提示词内容
        system_prompt = None
        if agent_data:
            prompt_info = agent_data.get("prompt")
            if prompt_info and prompt_info.get("content"):
                system_prompt = prompt_info.get("content")
                logger.info(f"从Agent配置获取提示词: {prompt_info.get('name', '未命名')}")

        await _init_async_checkpointer()
        checkpointer = _async_checkpointer if enable_memory else None
        
        if enable_memory:
            logger.info(f"记忆功能已启用，使用异步 Redis checkpoint: conversation={conversation}")
        else:
            logger.info(f"记忆功能已禁用，不使用 checkpoint: conversation={conversation}")

        # 使用 langchain_mcp_adapters 从 MCP 服务器获取真实工具列表
        tools = []
        logger.info(f"工具ID列表: {tool_ids}")
        if tool_ids:
            db = AgentService._get_session()
            try:
                # 按 mcp_id 分组工具名称
                mcp_tool_groups = {}
                for tool_id in tool_ids:
                    tool = MCPToolRepo.get_by_id(db, tool_id)
                    if tool:
                        mcp_id = tool.mcp_id
                        if mcp_id not in mcp_tool_groups:
                            mcp_tool_groups[mcp_id] = []
                        mcp_tool_groups[mcp_id].append(tool.name)
                
                if mcp_tool_groups:
                    logger.info(f"按MCP分组: {mcp_tool_groups}")
                    tools = AgentService._load_mcp_tools_sync(mcp_tool_groups)
                    logger.info(f"从MCP加载了 {len(tools)} 个工具")
            finally:
                db.close()
        
        ai_response_parts = []

        # 异步流式输出并收集响应
        logger.info(f"调用 get_deepagent_response_with_stream_async，tools: {tools}, enable_memory={enable_memory}")
        try:
            async for data in get_deepagent_response_with_stream_async(
                skill_sources=skill_sources,
                filesystem_backend=filesystem_backend,
                checkpointer=checkpointer,
                conversation=conversation,
                content=content,
                temperature=temperature,
                top_p=top_p,
                tools=tools,
                model_id=model_id,
                use_memory=enable_memory,
                system_prompt=system_prompt
            ):
                yield data
                # 收集token用于保存到数据库
                try:
                    parsed = json.loads(data.replace('data: ', ''))
                    if parsed.get('type') == 'token':
                        ai_response_parts.append(parsed.get('content', ''))
                except:
                    pass
        except asyncio.CancelledError:
            logger.info(f"异步聊天流被用户终止: conversation={conversation}")
            raise
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"异步聊天流错误: {error_msg}")

            # 检查是否是 LangGraph Redis 序列化器错误
            if "_encode_constructor_args" in error_msg or "JsonPlusRedisSerializer" in error_msg:
                logger.error(f"AgentService 捕获到 LangGraph Redis 序列化器错误: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'content': '会话存储出现兼容性问题，请使用新的会话 ID 重试'}, ensure_ascii=False)}\n\n"
                return

            # 检查是否是 DeepSeek 推理模式错误
            if "reasoning_content" in error_msg or "thinking mode" in error_msg:
                logger.error(f"AgentService 捕获到 DeepSeek 推理模式错误: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'content': '当前模型启用了推理模式，但会话不支持推理内容传递。请使用新的会话 ID 重试。'}, ensure_ascii=False)}\n\n"
                return

            # 其他错误重新抛出
            raise

        # 保存对话记录到数据库
        logger.info(f"准备保存对话记录: agent_id={agent_id}, user_id={user_id}, ai_response长度={len(ai_response_parts)}")
        if agent_id and user_id:
            try:
                db = SessionLocal()
                ai_message = "".join(ai_response_parts)
                logger.info(f"保存对话记录: agent_id={agent_id}, user_id={user_id}, conversation={conversation}")
                result = ChatRepo.create(db, {
                    "agent_id": agent_id,
                    "user_id": user_id,
                    "user_message": content,
                    "ai_message": ai_message,
                    "conversation_id": conversation
                })
                logger.info(f"对话记录保存成功: id={result.id}")
                db.close()
            except Exception as e:
                logger.exception(f"保存对话记录失败: {e}")
        else:
            logger.warning(f"无法保存对话记录: agent_id={agent_id}, user_id={user_id}, 参数缺失")


    @staticmethod
    def export_agents_json() -> str:
        """将所有Agent导出为JSON字符串"""
        agents = AgentService.list_all_agents()
        all_skills = SkillService.list_all_skills()
        skill_map = {s["id"]: s["name"] for s in all_skills}

        export_data = []
        for ag in agents:
            export_data.append(AgentService._build_agent_export_dict(ag, skill_map))

        return json.dumps({
            "export_time": datetime.now().isoformat(),
            "agents": export_data
        }, ensure_ascii=False, indent=2)

    @staticmethod
    def export_single_agent_json(agent_id: str) -> str:
        """导出单个Agent为JSON字符串"""
        agents = AgentService.list_all_agents()
        all_skills = SkillService.list_all_skills()
        skill_map = {s["id"]: s["name"] for s in all_skills}

        agent = None
        for ag in agents:
            if ag["id"] == agent_id:
                agent = ag
                break
        if not agent:
            return json.dumps({"error": "Agent not found"}, ensure_ascii=False)

        return json.dumps({
            "export_time": datetime.now().isoformat(),
            "agents": [AgentService._build_agent_export_dict(agent, skill_map)]
        }, ensure_ascii=False, indent=2)

    @staticmethod
    def _build_agent_export_dict(ag: dict, skill_map: dict) -> dict:
        return {
            "id": ag["id"],
            "name": ag["name"],
            "description": ag["description"],
            "skills": ag.get("skills", []),
            "skill_names": [skill_map.get(sid, "") for sid in ag.get("skills", [])],
            "config": ag.get("config", {}),
            "status": ag.get("status", "active"),
            "createdAt": ag.get("createdAt", ""),
            "updatedAt": ag.get("updatedAt", "")
        }

    @staticmethod
    def import_agents_json(json_str: str, user_id: str = None, department_id: str = None) -> Dict[str, Any]:
        """从JSON字符串导入Agent，返回导入结果统计"""
        result = {"success": 0, "skipped": 0, "errors": []}

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            result["errors"].append(f"JSON解析失败: {e}")
            return result

        agents_data = data.get("agents", [])
        if not agents_data:
            result["errors"].append("未找到agents数据")
            return result

        # 保存JSON文件到config/agent_config/
        agent_config_dir = AgentService.AGENT_CONFIG_DIR
        agent_config_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"agents_import_{timestamp}.json"
        file_path = agent_config_dir / file_name
        try:
            file_path.write_text(json_str, encoding='utf-8')
        except Exception as e:
            result["errors"].append(f"保存JSON文件失败: {e}")

        all_skills = SkillService.list_all_skills()
        skill_by_name = {s["name"]: s["id"] for s in all_skills}

        db = AgentService._get_session()
        try:
            for ag in agents_data:
                agent_name = ag.get("name", "").strip()
                if not agent_name:
                    result["errors"].append(f"Agent 缺少配置名称（name），跳过")
                    continue

                # 检查是否已存在同名Agent
                existing = AgentRepo.get_by_name(db, agent_name)
                if existing:
                    # 更新可见范围
                    update_dict = {}
                    if "agent_space" in ag and ag["agent_space"]:
                        update_dict["type"] = ag["agent_space"]
                    if update_dict:
                        AgentRepo.update(db, existing.agent_id, update_dict)
                        result["success"] += 1
                    else:
                        result["skipped"] += 1
                    continue

                # 生成新的agent_id
                new_agent_id = f"agent_{uuid.uuid4().hex}"

                skill_ids = []
                for sid in ag.get("skills", []):
                    if any(s["id"] == sid for s in all_skills):
                        skill_ids.append(sid)
                for sname in ag.get("skill_names", []):
                    if sname and sname in skill_by_name:
                        sid = skill_by_name[sname]
                        if sid not in skill_ids:
                            skill_ids.append(sid)

                created_at = None
                updated_at = None
                created_str = ag.get("createdAt", "")
                updated_str = ag.get("updatedAt", "")
                if created_str:
                    try:
                        created_at = datetime.fromisoformat(created_str)
                    except ValueError:
                        created_at = datetime.now()
                if updated_str:
                    try:
                        updated_at = datetime.fromisoformat(updated_str)
                    except ValueError:
                        updated_at = datetime.now()

                agent_dict = {
                    "agent_id": new_agent_id,
                    "name": agent_name,
                    "description": ag.get("description", ""),
                    "status": 1 if ag.get("status", "active") == "active" else 0,
                    "config": ag.get("config", {}),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "created_by": user_id,
                    "department_id": department_id,
                    "type": ag.get("agent_space", "private")
                }
                agent = AgentRepo.create(db, agent_dict)
                if skill_ids:
                    AgentSkillMappingRepo.set_agent_skills(db, new_agent_id, skill_ids)

                result["success"] += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        return result
