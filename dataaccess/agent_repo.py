import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from dataaccess.models import AgentModel, AgentSkillMappingModel, AgentToolMappingModel, MCPToolModel, LLMModel


class AgentRepo:
    """Agent数据访问层"""

    @staticmethod
    def create(db: Session, agent_data: Dict[str, Any]) -> AgentModel:
        config_value = agent_data.get("config")
        if config_value is not None and not isinstance(config_value, str):
            config_value = json.dumps(config_value, ensure_ascii=False)
        
        # 处理model_id：空字符串转为None
        model_id = agent_data.get("model_id")
        if model_id == '' or model_id is None:
            model_id = None
        
        # 处理prompt_id：空字符串转为None
        prompt_id = agent_data.get("prompt_id")
        if prompt_id == '' or prompt_id is None:
            prompt_id = None
        
        agent = AgentModel(
            agent_id=agent_data.get("agent_id", f"agent_{uuid.uuid4()}"),
            name=agent_data.get("name", ""),
            description=agent_data.get("description", ""),
            status=agent_data.get("status", 1),
            config=config_value,
            model_id=model_id,
            prompt_id=prompt_id,
            temperature=agent_data.get("temperature", 0.7),
            top_p=agent_data.get("top_p", 0.9),
            enable_memory=agent_data.get("enable_memory", True),
            type=agent_data.get("type", "private"),
            created_by=agent_data.get("created_by"),
            department_id=agent_data.get("department_id"),
            created_at=agent_data.get("created_at", datetime.now()),
            updated_at=agent_data.get("updated_at", datetime.now())
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def get_by_id(db: Session, agent_id: str) -> Optional[AgentModel]:
        return db.query(AgentModel).filter(AgentModel.agent_id == agent_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[AgentModel]:
        return db.query(AgentModel).filter(AgentModel.name == name).first()

    @staticmethod
    def get_all(db: Session) -> List[AgentModel]:
        return db.query(AgentModel).order_by(AgentModel.created_at.desc()).all()

    @staticmethod
    def get_all_paginated(db: Session, offset: int, limit: int) -> List[AgentModel]:
        return db.query(AgentModel).order_by(AgentModel.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(func.count(AgentModel.agent_id)).scalar() or 0

    @staticmethod
    def get_visible_agents(db: Session, user_id: str, department_id: str = None) -> List[AgentModel]:
        """获取用户可见的Agent列表
        - public: 所有人可见
        - group: 同部门可见（需要department_id匹配）
        - private: 仅创建者可见
        """
        conditions = [
            (AgentModel.type == "public"),
            (AgentModel.created_by == user_id)
        ]
        # 同部门可见：type=group 且 department_id 匹配
        if department_id:
            conditions.append(
                ((AgentModel.type == "group") & (AgentModel.department_id == department_id))
            )
        query = db.query(AgentModel).filter(or_(*conditions))
        return query.order_by(AgentModel.created_at.desc()).all()

    @staticmethod
    def get_visible_agents_paginated(db: Session, user_id: str, department_id: str = None, offset: int = 0, limit: int = 10) -> List[AgentModel]:
        """分页获取用户可见的Agent列表"""
        conditions = [
            (AgentModel.type == "public"),
            (AgentModel.created_by == user_id)
        ]
        if department_id:
            conditions.append(
                ((AgentModel.type == "group") & (AgentModel.department_id == department_id))
            )
        query = db.query(AgentModel).filter(or_(*conditions))
        return query.order_by(AgentModel.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def count_visible_agents(db: Session, user_id: str, department_id: str = None) -> int:
        """统计用户可见的Agent数量"""
        conditions = [
            (AgentModel.type == "public"),
            (AgentModel.created_by == user_id)
        ]
        if department_id:
            conditions.append(
                ((AgentModel.type == "group") & (AgentModel.department_id == department_id))
            )
        query = db.query(func.count(AgentModel.agent_id)).filter(or_(*conditions))
        return query.scalar() or 0

    @staticmethod
    def search_visible_agents_paginated(db: Session, user_id: str, department_id: str = None, 
                                        keyword: str = None, offset: int = 0, limit: int = 10) -> List[AgentModel]:
        """分页搜索用户可见的Agent列表"""
        conditions = [
            (AgentModel.type == "public"),
            (AgentModel.created_by == user_id)
        ]
        if department_id:
            conditions.append(
                ((AgentModel.type == "group") & (AgentModel.department_id == department_id))
            )
        query = db.query(AgentModel).filter(or_(*conditions))
        
        # 添加搜索条件
        if keyword:
            search_filter = or_(
                AgentModel.name.ilike(f"%{keyword}%"),
                AgentModel.description.ilike(f"%{keyword}%")
            )
            query = query.filter(search_filter)
        
        return query.order_by(AgentModel.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def count_search_visible_agents(db: Session, user_id: str, department_id: str = None, keyword: str = None) -> int:
        """统计搜索条件下用户可见的Agent数量"""
        conditions = [
            (AgentModel.type == "public"),
            (AgentModel.created_by == user_id)
        ]
        if department_id:
            conditions.append(
                ((AgentModel.type == "group") & (AgentModel.department_id == department_id))
            )
        query = db.query(func.count(AgentModel.agent_id)).filter(or_(*conditions))
        
        # 添加搜索条件
        if keyword:
            search_filter = or_(
                AgentModel.name.ilike(f"%{keyword}%"),
                AgentModel.description.ilike(f"%{keyword}%")
            )
            query = query.filter(search_filter)
        
        return query.scalar() or 0

    @staticmethod
    def update(db: Session, agent_id: str, update_data: Dict[str, Any]) -> Optional[AgentModel]:
        agent = db.query(AgentModel).filter(AgentModel.agent_id == agent_id).first()
        if not agent:
            return None
        for key, value in update_data.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        agent.updated_at = datetime.now()
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def delete(db: Session, agent_id: str) -> bool:
        agent = db.query(AgentModel).filter(AgentModel.agent_id == agent_id).first()
        if not agent:
            return False
        db.delete(agent)
        db.commit()
        return True


class AgentSkillMappingRepo:
    """Agent-Skill映射数据访问层"""

    @staticmethod
    def create(db: Session, agent_id: str, skill_id: str) -> AgentSkillMappingModel:
        mapping = AgentSkillMappingModel(
            id=uuid.uuid4().hex[:16],
            agent_id=agent_id,
            skills_id=skill_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping

    @staticmethod
    def get_by_agent(db: Session, agent_id: str) -> List[AgentSkillMappingModel]:
        return db.query(AgentSkillMappingModel).filter(
            AgentSkillMappingModel.agent_id == agent_id
        ).all()

    @staticmethod
    def get_by_skill(db: Session, skill_id: str) -> List[AgentSkillMappingModel]:
        return db.query(AgentSkillMappingModel).filter(
            AgentSkillMappingModel.skills_id == skill_id
        ).all()

    @staticmethod
    def delete_by_agent(db: Session, agent_id: str) -> bool:
        db.query(AgentSkillMappingModel).filter(
            AgentSkillMappingModel.agent_id == agent_id
        ).delete()
        db.commit()
        return True

    @staticmethod
    def delete_by_skill(db: Session, skill_id: str) -> bool:
        db.query(AgentSkillMappingModel).filter(
            AgentSkillMappingModel.skills_id == skill_id
        ).delete()
        db.commit()
        return True

    @staticmethod
    def set_agent_skills(db: Session, agent_id: str, skill_ids: List[str]):
        """设置Agent关联的技能（先删除旧关联，再创建新关联）"""
        AgentSkillMappingRepo.delete_by_agent(db, agent_id)
        for skill_id in skill_ids:
            AgentSkillMappingRepo.create(db, agent_id, skill_id)


class AgentToolMappingRepo:
    """Agent-MCP工具映射数据访问层"""

    @staticmethod
    def create(db: Session, agent_id: str, tool_id: str) -> AgentToolMappingModel:
        mapping = AgentToolMappingModel(
            id=uuid.uuid4().hex,
            agent_id=agent_id,
            tool_id=tool_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping

    @staticmethod
    def get_by_agent(db: Session, agent_id: str) -> List[AgentToolMappingModel]:
        return db.query(AgentToolMappingModel).filter(
            AgentToolMappingModel.agent_id == agent_id
        ).all()

    @staticmethod
    def get_by_tool(db: Session, tool_id: str) -> List[AgentToolMappingModel]:
        return db.query(AgentToolMappingModel).filter(
            AgentToolMappingModel.tool_id == tool_id
        ).all()

    @staticmethod
    def delete_by_agent(db: Session, agent_id: str) -> bool:
        db.query(AgentToolMappingModel).filter(
            AgentToolMappingModel.agent_id == agent_id
        ).delete()
        db.commit()
        return True

    @staticmethod
    def delete_by_tool(db: Session, tool_id: str) -> bool:
        db.query(AgentToolMappingModel).filter(
            AgentToolMappingModel.tool_id == tool_id
        ).delete()
        db.commit()
        return True

    @staticmethod
    def set_agent_tools(db: Session, agent_id: str, tool_ids: List[str]):
        """设置Agent关联的工具（先删除旧关联，再创建新关联）"""
        AgentToolMappingRepo.delete_by_agent(db, agent_id)
        for tool_id in tool_ids:
            AgentToolMappingRepo.create(db, agent_id, tool_id)


class MCPToolRepo:
    """MCP工具数据访问层"""

    @staticmethod
    def get_by_id(db: Session, tool_id: str) -> Optional[MCPToolModel]:
        return db.query(MCPToolModel).filter(MCPToolModel.id == tool_id).first()

    @staticmethod
    def get_all(db: Session) -> List[MCPToolModel]:
        return db.query(MCPToolModel).all()

    @staticmethod
    def get_by_mcp_id(db: Session, mcp_id: str) -> List[MCPToolModel]:
        return db.query(MCPToolModel).filter(MCPToolModel.mcp_id == mcp_id).all()


class LLMModelRepo:
    """LLM模型数据访问层"""

    @staticmethod
    def get_by_id(db: Session, model_id: str) -> Optional[LLMModel]:
        return db.query(LLMModel).filter(LLMModel.id == model_id).first()

    @staticmethod
    def get_all(db: Session) -> List[LLMModel]:
        return db.query(LLMModel).all()
