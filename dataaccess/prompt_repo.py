import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from dataaccess.models import PromptModel


class PromptRepo:
    """Prompt数据访问层"""

    @staticmethod
    def create(db: Session, prompt_data: Dict[str, Any]) -> PromptModel:
        prompt = PromptModel(
            id=prompt_data.get("id", str(uuid.uuid4())),
            name=prompt_data.get("name", ""),
            content=prompt_data.get("content", ""),
            description=prompt_data.get("description", ""),
            is_active=prompt_data.get("is_active", True),
            type=prompt_data.get("type", "private"),
            created_by=prompt_data.get("created_by"),
            department_id=prompt_data.get("department_id"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        return prompt

    @staticmethod
    def get_by_id(db: Session, prompt_id: str) -> Optional[PromptModel]:
        return db.query(PromptModel).filter(PromptModel.id == prompt_id).first()

    @staticmethod
    def get_all(db: Session) -> List[PromptModel]:
        return db.query(PromptModel).order_by(PromptModel.created_at.desc()).all()

    @staticmethod
    def get_all_active(db: Session) -> List[PromptModel]:
        return db.query(PromptModel).filter(PromptModel.is_active == True).order_by(PromptModel.created_at.desc()).all()

    @staticmethod
    def update(db: Session, prompt_id: str, update_data: Dict[str, Any]) -> Optional[PromptModel]:
        prompt = db.query(PromptModel).filter(PromptModel.id == prompt_id).first()
        if not prompt:
            return None
        for key, value in update_data.items():
            if hasattr(prompt, key):
                setattr(prompt, key, value)
        prompt.updated_at = datetime.now()
        db.commit()
        db.refresh(prompt)
        return prompt

    @staticmethod
    def delete(db: Session, prompt_id: str) -> bool:
        prompt = db.query(PromptModel).filter(PromptModel.id == prompt_id).first()
        if not prompt:
            return False
        db.delete(prompt)
        db.commit()
        return True

    @staticmethod
    def get_all_paginated(db: Session, offset: int, limit: int) -> List[PromptModel]:
        return db.query(PromptModel).order_by(PromptModel.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(func.count(PromptModel.id)).scalar() or 0

    @staticmethod
    def get_visible_prompts(db: Session, user_id: str, department_id: str = None) -> List[PromptModel]:
        """获取用户可见的Prompt列表
        - public: 所有人可见
        - group: 同部门可见（需要department_id匹配）
        - private: 仅创建者可见
        """
        conditions = [
            or_(
                PromptModel.type == "public",
                PromptModel.created_by == user_id
            )
        ]
        if department_id:
            conditions.append(
                and_(PromptModel.type == "group", PromptModel.department_id == department_id)
            )
        query = db.query(PromptModel).filter(or_(*conditions))
        return query.order_by(PromptModel.created_at.desc()).all()

    @staticmethod
    def get_visible_prompts_paginated(db: Session, user_id: str, department_id: str = None, 
                                       offset: int = 0, limit: int = 10, 
                                       keyword: str = None,
                                       is_active: bool = None) -> List[PromptModel]:
        """分页获取用户可见的Prompt列表"""
        conditions = [
            or_(
                PromptModel.type == "public",
                PromptModel.created_by == user_id
            )
        ]
        if department_id:
            conditions.append(
                and_(PromptModel.type == "group", PromptModel.department_id == department_id)
            )
        
        query = db.query(PromptModel).filter(or_(*conditions))
        
        if is_active is not None:
            query = query.filter(PromptModel.is_active == is_active)
        
        if keyword:
            query = query.filter(or_(
                PromptModel.name.contains(keyword),
                PromptModel.description.contains(keyword)
            ))
        
        return query.order_by(PromptModel.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def count_visible_prompts(db: Session, user_id: str, department_id: str = None, 
                               keyword: str = None,
                               is_active: bool = None) -> int:
        """统计用户可见的Prompt数量"""
        conditions = [
            or_(
                PromptModel.type == "public",
                PromptModel.created_by == user_id
            )
        ]
        if department_id:
            conditions.append(
                and_(PromptModel.type == "group", PromptModel.department_id == department_id)
            )
        
        query = db.query(func.count(PromptModel.id)).filter(or_(*conditions))
        
        if is_active is not None:
            query = query.filter(PromptModel.is_active == is_active)
        
        if keyword:
            query = query.filter(or_(
                PromptModel.name.contains(keyword),
                PromptModel.description.contains(keyword)
            ))
        
        return query.scalar() or 0
