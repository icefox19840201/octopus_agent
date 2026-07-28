import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from dataaccess.models import ChatMessageModel


class ChatRepo:
    """对话消息数据访问层"""

    @staticmethod
    def create(db: Session, data: Dict[str, Any]) -> ChatMessageModel:
        """创建对话记录"""
        message = ChatMessageModel(
            id=uuid.uuid4().hex,
            agent_id=data.get("agent_id"),
            user_id=data.get("user_id"),
            user_message=data.get("user_message", ""),
            ai_message=data.get("ai_message", ""),
            conversation_id=data.get("conversation_id"),
            created_at=datetime.now()
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_by_conversation(db: Session, conversation_id: str, limit: int = 100) -> List[ChatMessageModel]:
        """根据会话ID获取对话历史"""
        return db.query(ChatMessageModel).filter(
            ChatMessageModel.conversation_id == conversation_id
        ).order_by(ChatMessageModel.created_at.asc()).limit(limit).all()

    @staticmethod
    def get_by_user(db: Session, user_id: str, limit: int = 100) -> List[ChatMessageModel]:
        """根据用户ID获取对话历史"""
        return db.query(ChatMessageModel).filter(
            ChatMessageModel.user_id == user_id
        ).order_by(ChatMessageModel.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_by_agent(db: Session, agent_id: str, limit: int = 100) -> List[ChatMessageModel]:
        """根据智能体ID获取对话历史"""
        return db.query(ChatMessageModel).filter(
            ChatMessageModel.agent_id == agent_id
        ).order_by(ChatMessageModel.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_by_user_and_agent(db: Session, user_id: str, agent_id: str, limit: int = 100) -> List[ChatMessageModel]:
        """根据用户ID和智能体ID获取对话历史（时间从早到晚）"""
        return db.query(ChatMessageModel).filter(
            ChatMessageModel.user_id == user_id,
            ChatMessageModel.agent_id == agent_id
        ).order_by(ChatMessageModel.created_at.asc()).limit(limit).all()

    @staticmethod
    def get_by_user_agent_and_conversation(db: Session, user_id: str, agent_id: str, conversation_id: str, limit: int = 100) -> List[ChatMessageModel]:
        """根据用户ID、智能体ID和会话ID获取对话历史（时间从早到晚）"""
        return db.query(ChatMessageModel).filter(
            ChatMessageModel.user_id == user_id,
            ChatMessageModel.agent_id == agent_id,
            ChatMessageModel.conversation_id == conversation_id
        ).order_by(ChatMessageModel.created_at.asc()).limit(limit).all()

    @staticmethod
    def delete_by_conversation(db: Session, conversation_id: str) -> bool:
        """删除会话的所有对话记录"""
        db.query(ChatMessageModel).filter(
            ChatMessageModel.conversation_id == conversation_id
        ).delete()
        db.commit()
        return True
