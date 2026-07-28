import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from dataaccess.models import PermissionModel


class PermissionRepo:
    """权限数据访问层"""

    @staticmethod
    def create(db: Session, perm_data: Dict[str, Any]) -> PermissionModel:
        """创建权限"""
        perm = PermissionModel(
            id=perm_data.get("id", f"perm_{uuid.uuid4().hex[:16]}"),
            key=perm_data["key"],
            name=perm_data["name"],
            is_menu=perm_data.get("is_menu", False),
            menu_path=perm_data.get("menu_path"),
            menu_icon=perm_data.get("menu_icon"),
            menu_order=perm_data.get("menu_order", 0),
            status=perm_data.get("status", "active"),
            created_at=datetime.now()
        )
        db.add(perm)
        db.commit()
        db.refresh(perm)
        return perm

    @staticmethod
    def get_by_id(db: Session, perm_id: str) -> Optional[PermissionModel]:
        """根据ID获取权限"""
        return db.query(PermissionModel).filter(PermissionModel.id == perm_id).first()

    @staticmethod
    def get_by_key(db: Session, key: str) -> Optional[PermissionModel]:
        """根据标识获取权限"""
        return db.query(PermissionModel).filter(PermissionModel.key == key).first()

    @staticmethod
    def get_all(db: Session) -> List[PermissionModel]:
        """获取所有权限"""
        return db.query(PermissionModel).order_by(PermissionModel.menu_order).all()

    @staticmethod
    def get_active(db: Session) -> List[PermissionModel]:
        """获取所有启用的权限"""
        return db.query(PermissionModel).filter(
            PermissionModel.status == "active"
        ).order_by(PermissionModel.menu_order).all()

    @staticmethod
    def get_menus(db: Session) -> List[PermissionModel]:
        """获取所有菜单权限"""
        return db.query(PermissionModel).filter(
            PermissionModel.is_menu == True,
            PermissionModel.status == "active"
        ).order_by(PermissionModel.menu_order).all()

    @staticmethod
    def update(db: Session, perm_id: str, update_data: Dict[str, Any]) -> Optional[PermissionModel]:
        """更新权限"""
        perm = db.query(PermissionModel).filter(PermissionModel.id == perm_id).first()
        if not perm:
            return None
        for key, value in update_data.items():
            if hasattr(perm, key):
                setattr(perm, key, value)
        db.commit()
        db.refresh(perm)
        return perm

    @staticmethod
    def delete(db: Session, perm_id: str) -> bool:
        """删除权限"""
        perm = db.query(PermissionModel).filter(PermissionModel.id == perm_id).first()
        if not perm:
            return False
        db.delete(perm)
        db.commit()
        return True

    @staticmethod
    def count_all(db: Session) -> int:
        """统计权限数量"""
        return db.query(func.count(PermissionModel.id)).scalar() or 0

    @staticmethod
    def get_modules(db: Session) -> List[str]:
        """获取所有模块（已废弃）"""
        return []
