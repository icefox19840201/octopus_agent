import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from dataaccess.models import UserModel


class UserRepo:
    """用户数据访问层"""

    @staticmethod
    def create(db: Session, user_data: Dict[str, Any]) -> UserModel:
        """创建用户"""
        user = UserModel(
            id=user_data.get("id", f"user_{uuid.uuid4().hex[:16]}"),
            username=user_data["username"],
            email=user_data.get("email"),
            password_hash=user_data["password_hash"],
            real_name=user_data.get("real_name"),
            phone=user_data.get("phone"),
            department_id=user_data.get("department_id"),
            status=user_data.get("status", "active"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[UserModel]:
        """根据用户名获取用户"""
        return db.query(UserModel).filter(UserModel.username == username).first()

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[UserModel]:
        """根据用户ID获取用户"""
        return db.query(UserModel).filter(UserModel.id == user_id).first()

    @staticmethod
    def get_all(db: Session) -> List[UserModel]:
        """获取所有用户"""
        return db.query(UserModel).order_by(UserModel.created_at.desc()).all()

    @staticmethod
    def get_by_department(db: Session, dept_id: str) -> List[UserModel]:
        """根据部门获取用户"""
        return db.query(UserModel).filter(
            UserModel.department_id == dept_id
        ).order_by(UserModel.created_at.desc()).all()

    @staticmethod
    def update(db: Session, user_id: str, update_data: Dict[str, Any]) -> Optional[UserModel]:
        """更新用户"""
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            return None
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.updated_at = datetime.now()
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete(db: Session, user_id: str) -> bool:
        """删除用户"""
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True

    @staticmethod
    def count_all(db: Session) -> int:
        """统计用户数量"""
        return db.query(func.count(UserModel.id)).scalar() or 0

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest() == password_hash

    @staticmethod
    def hash_password(password: str) -> str:
        """对密码进行哈希"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @staticmethod
    def update_password(db: Session, user_id: str, new_hash: str) -> bool:
        """更新用户密码"""
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            user.password_hash = new_hash
            db.commit()
            return True
        return False
