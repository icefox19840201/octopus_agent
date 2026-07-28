from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session
from dataaccess.database import get_db
from biziness.mcp_service import MCPService
from utils.auth_decorator import require_auth, get_current_user
from utils.logger import logger
from dataaccess.mcp_repo import MCPRepo, MCPToolRepo
from langchain_mcp_adapters.client import MultiServerMCPClient
from dataaccess.agent_repo import AgentToolMappingRepo
import json
@require_auth
async def create_mcp(request: Request, db: Session = Depends(get_db)):
    """创建MCP服务配置"""
    user = get_current_user(request)
    return await MCPService.create_mcp(db, request, user)


@require_auth
async def list_mcps(request: Request, db: Session = Depends(get_db)):
    """获取MCP服务列表（分页，带权限过滤）"""

    logger.info(f"list_mcps view called")
    # 从查询参数中获取分页参数
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    
    # 获取当前用户ID和部门ID
    user = get_current_user(request)
    user_id = user.get('user_id') if user else None
    department_id = user.get('department_id') if user else None
    logger.info(f"list_mcps view: user_id={user_id}, department_id={department_id}")
    
    result = MCPService.list_mcps(db, page, page_size, user_id, department_id)
    logger.info(f"list_mcps view result: {result}")
    return result


@require_auth
async def get_mcp(request: Request, mcp_id: str, db: Session = Depends(get_db)):
    """获取MCP服务详情"""
    # 获取当前用户ID和部门ID
    user = get_current_user(request)
    user_id = user.get('user_id') if user else None
    department_id = user.get('department_id') if user else None
    
    return MCPService.get_mcp(db, mcp_id, user_id, department_id)


@require_auth
async def update_mcp(request: Request, mcp_id: str, db: Session = Depends(get_db)):
    """更新MCP服务配置"""
    user = get_current_user(request)
    return await MCPService.update_mcp(db, request, mcp_id, user)


@require_auth
async def delete_mcp(request: Request, mcp_id: str, db: Session = Depends(get_db)):
    """删除MCP服务配置"""
    try:
        # 获取当前用户ID
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None
        
        result = MCPService.delete_mcp(db, mcp_id, user_id)
        
        if result.get("code") == 200:
            return {"success": True, "message": result.get("message", "删除成功")}
        else:
            return {"success": False, "message": result.get("message", "删除失败")}
    except HTTPException as e:
        return {"success": False, "message": e.detail}
    except Exception as e:
        return {"success": False, "message": str(e)}


@require_auth
async def sync_mcp_tools(request: Request, mcp_id: str, db: Session = Depends(get_db)):
    """同步MCP工具信息"""
    # 获取当前用户ID
    user = get_current_user(request)
    user_id = user.get('user_id') if user else None
    
    return await MCPService.sync_mcp_tools(db, mcp_id, user_id)


@require_auth
async def list_mcp_tools(request: Request, mcp_id: str, db: Session = Depends(get_db)):
    """获取MCP工具列表"""
    user = get_current_user(request)
    user_id = user.get('user_id') if user else None
    department_id = user.get('department_id') if user else None
    
    logger.info(f"list_mcp_tools view: mcp_id={mcp_id}, user_id={user_id}")
    
    # 检查MCP访问权限
    mcp = MCPService.get_mcp(db, mcp_id, user_id, department_id)
    if mcp.get('code') != 200:
        return mcp
    
    tools = MCPToolRepo.get_by_mcp_id(db, mcp_id)
    tools_list = []
    for tool in tools:
        import json
        params = None
        if tool.parameters:
            try:
                params = json.loads(tool.parameters)
                logger.info(f"Tool {tool.name} parameters: {params}")
            except Exception as e:
                logger.error(f"Failed to parse parameters for tool {tool.name}: {e}")
        tools_list.append({
            'id': tool.id,
            'name': tool.name,
            'description': tool.description,
            'parameters': params,
            'createdAt': tool.created_at.strftime('%Y-%m-%d %H:%M:%S') if tool.created_at else None
        })
    
    return {"code": 200, "message": "获取成功", "data": {"tools": tools_list, "count": len(tools_list)}}


@require_auth
async def invoke_mcp_tool(request: Request, mcp_id: str, tool_name: str, db: Session = Depends(get_db)):
    """调用MCP工具"""
    user = get_current_user(request)
    user_id = user.get('user_id') if user else None
    department_id = user.get('department_id') if user else None
    
    logger.info(f"invoke_mcp_tool view: mcp_id={mcp_id}, tool_name={tool_name}, user_id={user_id}")
    
    # 检查MCP访问权限
    mcp_result = MCPService.get_mcp(db, mcp_id, user_id, department_id)
    if mcp_result.get('code') != 200:
        return mcp_result
    
    # 获取工具信息
    tool = MCPToolRepo.get_by_name_and_mcp(db, mcp_id, tool_name)
    if not tool:
        return {"code": 404, "message": "工具不存在"}
    
    # 获取请求参数
    try:
        body = await request.json()
        parameters = body.get('parameters', {})
    except:
        parameters = {}
    
    # 调用工具
    try:
        mcp = MCPRepo.get_by_id(db, mcp_id)
        server_name = mcp.name or f"mcp_{mcp_id}"
        
        if mcp.type == 'sse':
            connection_config = {
                server_name: {
                    "transport": "sse",
                    "url": mcp.endpoint
                }
            }
        elif mcp.type == 'streamable-http':
            connection_config = {
                server_name: {
                    "transport": "http",
                    "url": mcp.endpoint
                }
            }
        else:
            return {"code": 400, "message": f"不支持的MCP类型: {mcp.type}"}
        
        logger.info(f"正在调用工具: {tool_name}, 参数: {parameters}")
        
        # 创建客户端并调用工具
        client = MultiServerMCPClient(connection_config)
        tools = await client.get_tools()
        
        # 找到目标工具
        target_tool = None
        for t in tools:
            if getattr(t, 'name', '') == tool_name:
                target_tool = t
                break
        
        if not target_tool:
            return {"code": 404, "message": "工具在MCP服务器上不存在"}
        
        # 调用工具
        result = await target_tool.ainvoke(parameters)
        
        logger.info(f"工具调用成功: {tool_name}")
        
        return {
            "code": 200,
            "message": "调用成功",
            "data": {
                "result": result,
                "tool_name": tool_name,
                "parameters": parameters
            }
        }
        
    except Exception as e:
        logger.exception(f"调用工具失败: {e}")
        return {"code": 500, "message": f"调用失败: {str(e)}"}


@require_auth
async def get_all_mcp_tools(request: Request, agent_id: str = None, db: Session = Depends(get_db)):
    """获取MCP工具列表 - 如果传入agent_id，返回该智能体已绑定的工具；否则返回所有可用工具"""

    user = get_current_user(request)
    user_id = user.get('user_id') if user else None
    department_id = user.get('department_id') if user else None
    
    logger.info(f"get_all_mcp_tools view: user_id={user_id}, department_id={department_id}, agent_id={agent_id}")
    
    try:
        # 如果传入了agent_id，获取该智能体绑定的工具ID列表
        bound_tool_ids = set()
        if agent_id:
            bound_mappings = AgentToolMappingRepo.get_by_agent(db, agent_id)
            bound_tool_ids = {m.tool_id for m in bound_mappings}
            logger.info(f"智能体 {agent_id} 绑定的工具: {bound_tool_ids}")
        
        # 获取所有工具或只获取绑定的工具
        if bound_tool_ids:
            all_tools = []
            for tool_id in bound_tool_ids:
                tool = MCPToolRepo.get_by_id(db, tool_id)
                if tool:
                    all_tools.append(tool)
        else:
            all_tools = MCPToolRepo.get_all(db)
        
        tools_list = []
        
        for tool in all_tools:
            # 获取MCP服务信息
            mcp = MCPRepo.get_by_id(db, tool.mcp_id)
            if not mcp:
                continue
            
            # 只返回active状态的MCP服务器的工具
            if mcp.status != 'active':
                continue
                
            # 权限检查：public所有人可见，private仅创建者可见，group同部门可见
            if mcp.visibility == 'private' and mcp.created_by != user_id:
                continue
            if mcp.visibility == 'group' and mcp.department_id != department_id:
                continue
            
            params = None
            if tool.parameters:
                try:
                    params = json.loads(tool.parameters)
                except Exception as e:
                    logger.error(f"Failed to parse parameters for tool {tool.name}: {e}")
            
            tools_list.append({
                'id': tool.id,
                'name': tool.name,
                'description': tool.description,
                'parameters': params,
                'mcp_id': tool.mcp_id,
                'mcp_name': mcp.name,
                'createdAt': tool.created_at.strftime('%Y-%m-%d %H:%M:%S') if tool.created_at else None
            })
        
        return {"code": 200, "message": "获取成功", "data": {"tools": tools_list, "count": len(tools_list)}}
    except Exception as e:
        logger.exception(f"获取MCP工具失败: {e}")
        return {"code": 500, "message": f"获取失败: {str(e)}"}
