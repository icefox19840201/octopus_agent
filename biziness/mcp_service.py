import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
from dataaccess.mcp_repo import MCPRepo, MCPToolRepo
from dataaccess.role_repo import UserRoleRepo
from dataaccess.models import MCPModel, MCPToolModel, AgentToolMappingModel
from utils.logger import logger
from langchain_mcp_adapters.client import MultiServerMCPClient

class MCPService:
    """MCP服务管理类"""

    @staticmethod
    async def create_mcp(db: Session, request, user: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建MCP服务配置"""
        try:
            data = await request.json()
            if not data:
                raise HTTPException(status_code=400, detail="请求体不能为空")

            # 获取当前用户ID和部门ID
            user_id = user.get('user_id') if user else None
            department_id = user.get('department_id') if user else None

            # 生成唯一ID
            mcp_id = str(uuid.uuid4()).replace('-', '')[:32]

            # 准备数据
            mcp_data = {
                'id': mcp_id,
                'name': data.get('name', ''),
                'type': data.get('type', 'sse'),
                'endpoint': data.get('endpoint', ''),
                'description': data.get('description', ''),
                'visibility': data.get('visibility', 'private'),
                'created_by': user_id,
                'department_id': department_id,
                'status': 'stopped'
            }

            # 创建MCP服务
            mcp = MCPRepo.create(db, mcp_data)
            return {"code": 200, "message": "创建成功", "data": MCPService._mcp_to_dict(mcp)}
        except HTTPException:
            raise
        except Exception as e:
            return {"code": 500, "message": f"创建失败: {str(e)}"}

    @staticmethod
    def get_mcp(db: Session, mcp_id: str, user_id: str = None, department_id: str = None) -> Dict[str, Any]:
        """获取MCP服务详情"""
        try:
            mcp = MCPRepo.get_by_id(db, mcp_id)
            if not mcp:
                raise HTTPException(status_code=404, detail="MCP服务不存在")
            
            # 权限检查
            if user_id and not MCPService._has_permission(mcp, user_id, department_id):
                raise HTTPException(status_code=403, detail="无权访问此MCP服务")
            
            return {"code": 200, "message": "获取成功", "data": MCPService._mcp_to_dict(mcp)}
        except HTTPException:
            raise
        except Exception as e:
            return {"code": 500, "message": f"获取失败: {str(e)}"}

    @staticmethod
    def list_mcps(db: Session, page: int = 1, page_size: int = 10, 
                  user_id: str = None, department_id: str = None) -> Dict[str, Any]:
        """获取MCP服务列表（分页，带权限过滤）"""
        try:

            logger.info(f"list_mcps called: page={page}, page_size={page_size}, user_id={user_id}, department_id={department_id}")
            page_result = MCPRepo.get_page(db, page, page_size, user_id, department_id)
            items = [MCPService._mcp_to_dict(m) for m in page_result.items]
            logger.info(f"list_mcps result: {len(items)} items, total={page_result.total}")
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "items": items,
                    "total": page_result.total,
                    "page": page_result.page,
                    "page_size": page_result.page_size,
                    "total_pages": page_result.total_pages
                }
            }
        except Exception as e:
            logger.exception(f"list_mcps error: {e}")
            return {"code": 500, "message": f"获取失败: {str(e)}"}

    @staticmethod
    async def update_mcp(db: Session, request, mcp_id: str, user: Dict[str, Any] = None) -> Dict[str, Any]:
        """更新MCP服务配置"""
        try:
            data = await request.json()
            if not data:
                raise HTTPException(status_code=400, detail="请求体不能为空")

            # 获取当前用户ID
            user_id = user.get('user_id') if user else None
            
            # 检查MCP是否存在
            mcp = MCPRepo.get_by_id(db, mcp_id)
            if not mcp:
                raise HTTPException(status_code=404, detail="MCP服务不存在")
            
            # 权限检查：只有创建者可以修改
            if mcp.created_by != user_id:
                raise HTTPException(status_code=403, detail="无权修改此MCP服务")

            # 准备更新数据
            update_data = {}
            if 'name' in data:
                update_data['name'] = data['name']
            if 'type' in data:
                update_data['type'] = data['type']
            if 'endpoint' in data:
                update_data['endpoint'] = data['endpoint']
            if 'description' in data:
                update_data['description'] = data['description']
            if 'visibility' in data:
                update_data['visibility'] = data['visibility']
            if 'status' in data:
                update_data['status'] = data['status']

            mcp = MCPRepo.update(db, mcp_id, update_data)
            return {"code": 200, "message": "更新成功", "data": MCPService._mcp_to_dict(mcp)}
        except HTTPException:
            raise
        except Exception as e:
            return {"code": 500, "message": f"更新失败: {str(e)}"}

    @staticmethod
    def delete_mcp(db: Session, mcp_id: str, user_id: str = None) -> Dict[str, Any]:
        """删除MCP服务配置"""
        try:
            # 检查MCP是否存在
            mcp = MCPRepo.get_by_id(db, mcp_id)
            if not mcp:
                raise HTTPException(status_code=404, detail="MCP服务不存在")
            
            # 权限检查：只有创建者或管理员可以删除
            if user_id:
                is_admin = UserRoleRepo.is_user_admin(db, user_id)
                if mcp.created_by != user_id and not is_admin:
                    raise HTTPException(status_code=403, detail="无权删除，仅本人或管理员可以删除")

            # 检查该MCP服务下的工具是否有被智能体引用
            tools = MCPToolRepo.get_by_mcp_id(db, mcp_id)
            tool_ids = [tool.id for tool in tools]
            if tool_ids:
                agent_count = db.query(AgentToolMappingModel).filter(
                    AgentToolMappingModel.tool_id.in_(tool_ids)
                ).count()
                if agent_count > 0:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"当前MCP服务下的工具已有智能体引用，请先解除引用后再删除"
                    )

            success = MCPRepo.delete(db, mcp_id)
            if not success:
                raise HTTPException(status_code=404, detail="MCP服务不存在")
            return {"code": 200, "message": "删除成功"}
        except HTTPException:
            raise
        except Exception as e:
            return {"code": 500, "message": f"删除失败: {str(e)}"}

    @staticmethod
    def _has_permission(mcp: MCPModel, user_id: str, department_id: str = None) -> bool:
        """检查用户是否有权限访问MCP服务"""
        if mcp.visibility == 'public':
            return True
        elif mcp.visibility == 'private':
            return mcp.created_by == user_id
        elif mcp.visibility == 'group':
            return mcp.department_id == department_id
        return False

    @staticmethod
    def _mcp_to_dict(mcp: MCPModel) -> Dict[str, Any]:
        """将MCP模型转换为字典"""
        return {
            'id': mcp.id,
            'name': mcp.name,
            'type': mcp.type,
            'endpoint': mcp.endpoint,
            'description': mcp.description,
            'visibility': mcp.visibility,
            'created_by': mcp.created_by,
            'department_id': mcp.department_id,
            'status': mcp.status,
            'createdAt': mcp.created_at.strftime('%Y-%m-%d %H:%M:%S') if mcp.created_at else None,
            'updatedAt': mcp.updated_at.strftime('%Y-%m-%d %H:%M:%S') if mcp.updated_at else None
        }

    @staticmethod
    async def sync_mcp_tools(db: Session, mcp_id: str, user_id: str = None) -> Dict[str, Any]:
        """同步MCP工具信息"""
        try:
            # 获取MCP服务
            mcp = MCPRepo.get_by_id(db, mcp_id)
            if not mcp:
                raise HTTPException(status_code=404, detail="MCP服务不存在")
            
            # 权限检查：只有创建者可以同步
            if user_id and mcp.created_by != user_id:
                raise HTTPException(status_code=403, detail="无权同步此MCP服务")

            
            # 根据类型构建连接配置
            server_name = mcp.name or f"mcp_{mcp_id}"
            
            # 基础请求头 - 服务器需要这些头来接受请求
            base_headers = {
                "Accept": "application/json, text/event-stream",
                "Accept-Encoding": "identity"
            }
            
            if mcp.type == 'sse':
                connection_config = {
                    server_name: {
                        "transport": "sse",
                        "url": mcp.endpoint,
                        "headers": base_headers
                    }
                }
            elif mcp.type == 'streamable-http':
                connection_config = {
                    server_name: {
                        "transport": "streamable_http",
                        "url": mcp.endpoint,
                        "headers": base_headers
                    }
                }
            else:
                return {"code": 400, "message": f"不支持的MCP类型: {mcp.type}"}
            
            logger.info(f"正在同步MCP工具: {mcp.name}, 类型: {mcp.type}, 端点: {mcp.endpoint}")
            logger.info(f"连接配置: {connection_config}")
            
            # 创建客户端并获取工具
            try:
                client = MultiServerMCPClient(connection_config)
                tools = await client.get_tools()
            except Exception as conn_error:
                logger.error(f"MCP连接失败 - 类型: {mcp.type}, 端点: {mcp.endpoint}")
                logger.error(f"连接配置: {connection_config}")
                logger.error(f"错误详情: {conn_error}")
                raise
            
            # 提取工具信息
            tools_info = []
            for tool in tools:
                tool_info = {
                    'name': getattr(tool, 'name', ''),
                    'description': getattr(tool, 'description', ''),
                    'args_schema': getattr(tool, 'args_schema', None)
                }
                if tool_info['args_schema']:
                    try:
                        if hasattr(tool_info['args_schema'], 'model_json_schema'):
                            tool_info['args_schema'] = tool_info['args_schema'].model_json_schema()
                            logger.info(f"Tool {tool_info['name']} schema: {tool_info['args_schema']}")
                        else:
                            tool_info['args_schema'] = str(tool_info['args_schema'])
                    except Exception as e:
                        logger.error(f"Failed to convert schema for tool {tool_info['name']}: {e}")
                        tool_info['args_schema'] = str(tool_info['args_schema'])
                tools_info.append(tool_info)
            
            # 同步工具到数据库
            sync_result = MCPToolRepo.sync_tools(db, mcp_id, tools_info)
            
            # 更新MCP状态为 active
            MCPRepo.update(db, mcp_id, {'status': 'active'})
            
            logger.info(f"MCP工具同步成功: {mcp.name}, 获取到 {len(tools_info)} 个工具, "
                       f"新增{sync_result['added']}个, 更新{sync_result['updated']}个, "
                       f"删除{sync_result['deleted']}个, 未变更{sync_result['unchanged']}个")
            
            return {
                "code": 200,
                "message": f"同步成功，获取到 {len(tools_info)} 个工具",
                "data": {
                    "tools": tools_info,
                    "count": len(tools_info),
                    "sync_result": sync_result
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"同步MCP工具失败: {e}")
            # 更新状态为 stopped
            try:
                MCPRepo.update(db, mcp_id, {'status': 'stopped'})
            except:
                pass
            return {"code": 500, "message": f"同步失败: {str(e)}"}
