import uuid
import json
from sqlalchemy.orm import Session
from dataaccess.models import MCPModel, MCPToolModel
from typing import List, Optional, Dict, Any
from utils.pagination import paginate, PageResult


class MCPRepo:
    """MCP服务数据访问类"""

    @staticmethod
    def create(db: Session, data: Dict[str, Any]) -> MCPModel:
        """创建MCP服务配置"""
        mcp = MCPModel(**data)
        db.add(mcp)
        db.commit()
        db.refresh(mcp)
        return mcp

    @staticmethod
    def get_by_id(db: Session, mcp_id: str) -> Optional[MCPModel]:
        """根据ID获取MCP服务配置"""
        return db.query(MCPModel).filter(MCPModel.id == mcp_id).first()

    @staticmethod
    def get_page(db: Session, page: int = 1, page_size: int = 10, 
                 user_id: str = None, department_id: str = None) -> PageResult:
        """分页获取MCP服务配置（带权限过滤）"""
        offset, limit = paginate(page, page_size)
        query = db.query(MCPModel)
        
        # 权限过滤：public所有人可见，private仅自己可见，group同部门可见
        if user_id:
            query = query.filter(
                (MCPModel.visibility == 'public') |
                ((MCPModel.visibility == 'private') & (MCPModel.created_by == user_id)) |
                ((MCPModel.visibility == 'group') & (MCPModel.department_id == department_id))
            )
        else:
            # 未登录用户只能看到public的MCP
            query = query.filter(MCPModel.visibility == 'public')
        
        query = query.order_by(MCPModel.created_at.desc())
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return PageResult(items, total, page, page_size)

    @staticmethod
    def update(db: Session, mcp_id: str, data: Dict[str, Any]) -> Optional[MCPModel]:
        """更新MCP服务配置"""
        mcp = db.query(MCPModel).filter(MCPModel.id == mcp_id).first()
        if not mcp:
            return None
        for key, value in data.items():
            setattr(mcp, key, value)
        db.commit()
        db.refresh(mcp)
        return mcp

    @staticmethod
    def delete(db: Session, mcp_id: str) -> bool:
        """删除MCP服务配置"""
        mcp = db.query(MCPModel).filter(MCPModel.id == mcp_id).first()
        if not mcp:
            return False
        db.delete(mcp)
        db.commit()
        return True


class MCPToolRepo:
    """MCP工具数据访问类"""

    @staticmethod
    def create(db: Session, mcp_id: str, name: str, description: str = None, parameters: Dict = None) -> MCPToolModel:
        """创建MCP工具"""
        tool = MCPToolModel(
            id=str(uuid.uuid4()).replace('-', ''),
            mcp_id=mcp_id,
            name=name,
            description=description,
            parameters=json.dumps(parameters, ensure_ascii=False) if parameters else None
        )
        db.add(tool)
        db.commit()
        db.refresh(tool)
        return tool

    @staticmethod
    def get_by_id(db: Session, tool_id: str) -> Optional[MCPToolModel]:
        """根据ID获取MCP工具"""
        return db.query(MCPToolModel).filter(MCPToolModel.id == tool_id).first()

    @staticmethod
    def get_by_mcp_id(db: Session, mcp_id: str) -> List[MCPToolModel]:
        """根据MCP ID获取所有工具"""
        return db.query(MCPToolModel).filter(MCPToolModel.mcp_id == mcp_id).all()

    @staticmethod
    def get_all(db: Session) -> List[MCPToolModel]:
        """获取所有MCP工具"""
        return db.query(MCPToolModel).all()

    @staticmethod
    def get_by_name_and_mcp(db: Session, mcp_id: str, name: str) -> Optional[MCPToolModel]:
        """根据MCP ID和工具名称获取工具"""
        return db.query(MCPToolModel).filter(
            MCPToolModel.mcp_id == mcp_id,
            MCPToolModel.name == name
        ).first()

    @staticmethod
    def update(db: Session, tool_id: str, data: Dict[str, Any]) -> Optional[MCPToolModel]:
        """更新MCP工具"""
        tool = db.query(MCPToolModel).filter(MCPToolModel.id == tool_id).first()
        if not tool:
            return None
        for key, value in data.items():
            if key == 'parameters' and value is not None:
                setattr(tool, key, json.dumps(value, ensure_ascii=False))
            else:
                setattr(tool, key, value)
        db.commit()
        db.refresh(tool)
        return tool

    @staticmethod
    def delete_by_mcp_id(db: Session, mcp_id: str) -> int:
        """删除指定MCP的所有工具"""
        result = db.query(MCPToolModel).filter(MCPToolModel.mcp_id == mcp_id).delete()
        db.commit()
        return result

    @staticmethod
    def delete(db: Session, tool_id: str) -> bool:
        """删除MCP工具"""
        tool = db.query(MCPToolModel).filter(MCPToolModel.id == tool_id).first()
        if not tool:
            return False
        db.delete(tool)
        db.commit()
        return True

    @staticmethod
    def sync_tools(db: Session, mcp_id: str, tools_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """同步MCP工具列表
        
        Args:
            db: 数据库会话
            mcp_id: MCP服务ID
            tools_data: 工具列表数据，每个工具包含 name, description, parameters
            
        Returns:
            同步结果统计
        """
        # 获取现有工具
        existing_tools = MCPToolRepo.get_by_mcp_id(db, mcp_id)
        existing_map = {t.name: t for t in existing_tools}
        
        added = 0
        updated = 0
        unchanged = 0
        
        for tool_data in tools_data:
            name = tool_data.get('name')
            description = tool_data.get('description')
            parameters = tool_data.get('args_schema') or tool_data.get('parameters')
            
            if name in existing_map:
                # 更新现有工具
                tool = existing_map[name]
                # 检查是否有变化
                current_params = json.loads(tool.parameters) if tool.parameters else None
                if (tool.description != description or 
                    current_params != parameters):
                    MCPToolRepo.update(db, tool.id, {
                        'description': description,
                        'parameters': parameters
                    })
                    updated += 1
                else:
                    unchanged += 1
            else:
                # 创建新工具
                MCPToolRepo.create(db, mcp_id, name, description, parameters)
                added += 1
        
        # 删除不再存在的工具
        new_names = {t.get('name') for t in tools_data}
        deleted = 0
        for tool in existing_tools:
            if tool.name not in new_names:
                MCPToolRepo.delete(db, tool.id)
                deleted += 1
        
        return {
            'added': added,
            'updated': updated,
            'unchanged': unchanged,
            'deleted': deleted,
            'total': len(tools_data)
        }
