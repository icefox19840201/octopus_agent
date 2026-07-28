import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from dataaccess.models import SkillModel, AgentSkillMappingModel


class SkillRepo:
    """Skill数据访问层"""

    @staticmethod
    def create(db: Session, skill_data: Dict[str, Any]) -> SkillModel:
        skill = SkillModel(
            id=skill_data.get("id", uuid.uuid4()),
            skills_name=skill_data.get("skills_name", ""),
            skills_description=skill_data.get("skills_description", ""),
            skills_path=skill_data.get("skills_path", ""),
            type=skill_data.get("type", "private"),
            created_by=skill_data.get("created_by"),
            department_id=skill_data.get("department_id"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(skill)
        db.commit()
        db.refresh(skill)
        return skill

    @staticmethod
    def get_by_id(db: Session, skill_id: str) -> Optional[SkillModel]:
        return db.query(SkillModel).filter(SkillModel.id == skill_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[SkillModel]:
        return db.query(SkillModel).filter(SkillModel.skills_name == name).first()

    @staticmethod
    def get_all(db: Session) -> List[SkillModel]:
        return db.query(SkillModel).order_by(SkillModel.created_at.desc()).all()

    @staticmethod
    def update(db: Session, skill_id: str, update_data: Dict[str, Any]) -> Optional[SkillModel]:
        skill = db.query(SkillModel).filter(SkillModel.id == skill_id).first()
        if not skill:
            return None
        for key, value in update_data.items():
            if hasattr(skill, key):
                setattr(skill, key, value)
        skill.updated_at = datetime.now()
        db.commit()
        db.refresh(skill)
        return skill

    @staticmethod
    def get_all_paginated(db: Session, offset: int, limit: int) -> List[SkillModel]:
        return db.query(SkillModel).order_by(SkillModel.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(func.count(SkillModel.id)).scalar() or 0

    @staticmethod
    def get_visible_skills(db: Session, user_id: str, department_id: str = None) -> List[SkillModel]:
        """获取用户可见的Skill列表
        - public: 所有人可见
        - group: 同部门可见（需要department_id匹配）
        - private: 仅创建者可见
        """
        conditions = [
            (SkillModel.type == "public"),
            (SkillModel.created_by == user_id)
        ]
        # 同部门可见：type=group 且 department_id 匹配
        if department_id:
            conditions.append(
                ((SkillModel.type == "group") & (SkillModel.department_id == department_id))
            )
        query = db.query(SkillModel).filter(or_(*conditions))
        return query.order_by(SkillModel.created_at.desc()).all()

    @staticmethod
    def get_visible_skills_paginated(db: Session, user_id: str, department_id: str = None, offset: int = 0, limit: int = 10) -> List[SkillModel]:
        """分页获取用户可见的Skill列表"""
        conditions = [
            (SkillModel.type == "public"),
            (SkillModel.created_by == user_id)
        ]
        if department_id:
            conditions.append(
                ((SkillModel.type == "group") & (SkillModel.department_id == department_id))
            )
        query = db.query(SkillModel).filter(or_(*conditions))
        return query.order_by(SkillModel.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def count_visible_skills(db: Session, user_id: str, department_id: str = None) -> int:
        """统计用户可见的Skill数量"""
        conditions = [
            (SkillModel.type == "public"),
            (SkillModel.created_by == user_id)
        ]
        if department_id:
            conditions.append(
                ((SkillModel.type == "group") & (SkillModel.department_id == department_id))
            )
        query = db.query(func.count(SkillModel.id)).filter(or_(*conditions))
        return query.scalar() or 0

    @staticmethod
    def count_agent_references(db: Session, skill_id: str) -> int:
        return db.query(func.count(AgentSkillMappingModel.id)).filter(
            AgentSkillMappingModel.skills_id == skill_id
        ).scalar() or 0

    @staticmethod
    def delete(db: Session, skill_id: str) -> bool:
        skill = db.query(SkillModel).filter(SkillModel.id == skill_id).first()
        if not skill:
            return False
        db.delete(skill)
        db.commit()
        return True
