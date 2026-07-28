import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from dataaccess.models import KnowledgeBaseModel, KnowledgeDocumentModel


class KnowledgeBaseRepo:
    """知识库数据访问层"""

    @staticmethod
    def create(db: Session, kb_data: Dict[str, Any]) -> KnowledgeBaseModel:
        """创建知识库"""
        kb = KnowledgeBaseModel(
            id=kb_data.get("id", f"kb_{uuid.uuid4().hex[:16]}"),
            name=kb_data["name"],
            description=kb_data.get("description"),
            embedding_model=kb_data.get("embedding_model"),
            vector_store_path=kb_data.get("vector_store_path"),
            type=kb_data.get("type", "private"),
            created_by=kb_data.get("created_by"),
            department_id=kb_data.get("department_id"),
            status=kb_data.get("status", "active"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(kb)
        db.commit()
        db.refresh(kb)
        return kb

    @staticmethod
    def get_by_id(db: Session, kb_id: str) -> Optional[KnowledgeBaseModel]:
        """根据ID获取知识库"""
        return db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.id == kb_id).first()

    @staticmethod
    def get_visible_knowledge_bases(db: Session, user_id: str, department_id: Optional[str] = None, is_admin: bool = False) -> List[KnowledgeBaseModel]:
        """获取用户可见的知识库列表"""
        query = db.query(KnowledgeBaseModel)

        if not is_admin:
            conditions = [
                KnowledgeBaseModel.type == "public",
                KnowledgeBaseModel.created_by == user_id
            ]
            if department_id:
                conditions.append(
                    and_(
                        KnowledgeBaseModel.type == "group",
                        KnowledgeBaseModel.department_id == department_id
                    )
                )
            query = query.filter(or_(*conditions))

        return query.order_by(KnowledgeBaseModel.created_at.desc()).all()

    @staticmethod
    def update(db: Session, kb_id: str, update_data: Dict[str, Any]) -> Optional[KnowledgeBaseModel]:
        """更新知识库"""
        kb = db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.id == kb_id).first()
        if not kb:
            return None
        for key, value in update_data.items():
            if hasattr(kb, key):
                setattr(kb, key, value)
        kb.updated_at = datetime.now()
        db.commit()
        db.refresh(kb)
        return kb

    @staticmethod
    def delete(db: Session, kb_id: str) -> bool:
        """删除知识库"""
        kb = db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.id == kb_id).first()
        if not kb:
            return False
        db.delete(kb)
        db.commit()
        return True


class KnowledgeDocumentRepo:
    """知识库文档数据访问层"""

    @staticmethod
    def create(db: Session, doc_data: Dict[str, Any]) -> KnowledgeDocumentModel:
        """创建文档"""
        doc = KnowledgeDocumentModel(
            id=doc_data.get("id", f"doc_{uuid.uuid4().hex[:16]}"),
            kb_id=doc_data["kb_id"],
            title=doc_data["title"],
            content=doc_data.get("content"),
            file_path=doc_data.get("file_path"),
            file_type=doc_data.get("file_type"),
            chunk_count=doc_data.get("chunk_count", 0),
            status=doc_data.get("status", "active"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def get_by_id(db: Session, doc_id: str) -> Optional[KnowledgeDocumentModel]:
        """根据ID获取文档"""
        return db.query(KnowledgeDocumentModel).filter(KnowledgeDocumentModel.id == doc_id).first()

    @staticmethod
    def get_by_kb_id(db: Session, kb_id: str) -> List[KnowledgeDocumentModel]:
        """获取知识库下的所有文档"""
        return db.query(KnowledgeDocumentModel).filter(
            KnowledgeDocumentModel.kb_id == kb_id
        ).order_by(KnowledgeDocumentModel.created_at.desc()).all()

    @staticmethod
    def update(db: Session, doc_id: str, update_data: Dict[str, Any]) -> Optional[KnowledgeDocumentModel]:
        """更新文档"""
        doc = db.query(KnowledgeDocumentModel).filter(KnowledgeDocumentModel.id == doc_id).first()
        if not doc:
            return None
        for key, value in update_data.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        doc.updated_at = datetime.now()
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def delete(db: Session, doc_id: str) -> bool:
        """删除文档"""
        doc = db.query(KnowledgeDocumentModel).filter(KnowledgeDocumentModel.id == doc_id).first()
        if not doc:
            return False
        db.delete(doc)
        db.commit()
        return True
