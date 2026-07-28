from sqlalchemy.orm import Session
from dataaccess.models import LLMModel
from typing import List, Optional, Dict, Any, Tuple
from utils.pagination import paginate, PageResult


class LLMModelRepo:
    """LLM模型数据访问类"""

    @staticmethod
    def create(db: Session, data: Dict[str, Any]) -> LLMModel:
        """创建模型配置"""
        model = LLMModel(**data)
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def get_by_id(db: Session, model_id: str) -> Optional[LLMModel]:
        """根据ID获取模型配置"""
        return db.query(LLMModel).filter(LLMModel.id == model_id).first()

    @staticmethod
    def get_all(db: Session) -> List[LLMModel]:
        """获取所有模型配置"""
        return db.query(LLMModel).order_by(LLMModel.created_at.desc()).all()

    @staticmethod
    def get_page(db: Session, page: int = 1, page_size: int = 10) -> PageResult:
        """分页获取模型配置"""
        offset, limit = paginate(page, page_size)
        query = db.query(LLMModel).order_by(LLMModel.created_at.desc())
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return PageResult(items, total, page, page_size)

    @staticmethod
    def update(db: Session, model_id: str, data: Dict[str, Any]) -> Optional[LLMModel]:
        """更新模型配置"""
        model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
        if not model:
            return None
        for key, value in data.items():
            setattr(model, key, value)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def delete(db: Session, model_id: str) -> bool:
        """删除模型配置"""
        model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
        if not model:
            return False
        db.delete(model)
        db.commit()
        return True
