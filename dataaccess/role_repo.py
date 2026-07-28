import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from dataaccess.models import RoleModel, PermissionModel, RolePermissionMapping, UserRoleMapping


class RoleRepo:
    """角色数据访问层"""

    @staticmethod
    def create(db: Session, role_data: Dict[str, Any]) -> RoleModel:
        """创建角色"""
        role = RoleModel(
            id=role_data.get("id", f"role_{uuid.uuid4().hex[:16]}"),
            name=role_data["name"],
            code=role_data["code"],
            description=role_data.get("description"),
            status=role_data.get("status", "active"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def get_by_id(db: Session, role_id: str) -> Optional[RoleModel]:
        """根据ID获取角色"""
        return db.query(RoleModel).filter(RoleModel.id == role_id).first()

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[RoleModel]:
        """根据编码获取角色"""
        return db.query(RoleModel).filter(RoleModel.code == code).first()

    @staticmethod
    def get_all(db: Session) -> List[RoleModel]:
        """获取所有角色"""
        return db.query(RoleModel).order_by(RoleModel.created_at.desc()).all()

    @staticmethod
    def get_active(db: Session) -> List[RoleModel]:
        """获取所有启用的角色"""
        return db.query(RoleModel).filter(
            RoleModel.status == "active"
        ).order_by(RoleModel.created_at.desc()).all()

    @staticmethod
    def update(db: Session, role_id: str, update_data: Dict[str, Any]) -> Optional[RoleModel]:
        """更新角色"""
        role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
        if not role:
            return None
        for key, value in update_data.items():
            if hasattr(role, key):
                setattr(role, key, value)
        role.updated_at = datetime.now()
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def delete(db: Session, role_id: str) -> bool:
        """删除角色"""
        role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
        if not role:
            return False
        db.delete(role)
        db.commit()
        return True

    @staticmethod
    def count_all(db: Session) -> int:
        """统计角色数量"""
        return db.query(func.count(RoleModel.id)).scalar() or 0


class RolePermissionRepo:
    """角色权限关联数据访问层"""

    @staticmethod
    def set_role_permissions(db: Session, role_id: str, permission_ids: List[str]):
        """设置角色的权限（先删除再添加）"""
        # 删除现有权限
        db.query(RolePermissionMapping).filter(
            RolePermissionMapping.role_id == role_id
        ).delete()
        # 添加新权限
        for perm_id in permission_ids:
            mapping = RolePermissionMapping(
                id=f"rp_{uuid.uuid4().hex[:16]}",
                role_id=role_id,
                permission_id=perm_id,
                created_at=datetime.now()
            )
            db.add(mapping)
        db.commit()

    @staticmethod
    def get_role_permissions(db: Session, role_id: str) -> List[PermissionModel]:
        """获取角色的所有权限"""
        mappings = db.query(RolePermissionMapping).filter(
            RolePermissionMapping.role_id == role_id
        ).all()
        permission_ids = [m.permission_id for m in mappings]
        if not permission_ids:
            return []
        return db.query(PermissionModel).filter(
            PermissionModel.id.in_(permission_ids)
        ).all()

    @staticmethod
    def get_role_permission_ids(db: Session, role_id: str) -> List[str]:
        """获取角色的权限ID列表"""
        mappings = db.query(RolePermissionMapping).filter(
            RolePermissionMapping.role_id == role_id
        ).all()
        return [m.permission_id for m in mappings]


class UserRoleRepo:
    """用户角色关联数据访问层"""

    @staticmethod
    def set_user_roles(db: Session, user_id: str, role_ids: List[str]):
        """设置用户的角色（先删除再添加）"""
        # 删除现有角色
        db.query(UserRoleMapping).filter(
            UserRoleMapping.user_id == user_id
        ).delete()
        # 添加新角色
        for role_id in role_ids:
            mapping = UserRoleMapping(
                id=f"ur_{uuid.uuid4().hex[:16]}",
                user_id=user_id,
                role_id=role_id,
                created_at=datetime.now()
            )
            db.add(mapping)
        db.commit()

    @staticmethod
    def get_user_roles(db: Session, user_id: str) -> List[RoleModel]:
        """获取用户的所有角色"""
        mappings = db.query(UserRoleMapping).filter(
            UserRoleMapping.user_id == user_id
        ).all()
        role_ids = [m.role_id for m in mappings]
        if not role_ids:
            return []
        return db.query(RoleModel).filter(
            RoleModel.id.in_(role_ids)
        ).all()

    @staticmethod
    def get_user_role_ids(db: Session, user_id: str) -> List[str]:
        """获取用户的角色ID列表"""
        mappings = db.query(UserRoleMapping).filter(
            UserRoleMapping.user_id == user_id
        ).all()
        return [m.role_id for m in mappings]

    @staticmethod
    def get_user_permissions(db: Session, user_id: str) -> List[PermissionModel]:
        """获取用户的所有权限（通过角色）"""
        # 获取用户的所有角色ID
        role_ids = UserRoleRepo.get_user_role_ids(db, user_id)
        if not role_ids:
            return []
        # 获取这些角色的所有权限
        mappings = db.query(RolePermissionMapping).filter(
            RolePermissionMapping.role_id.in_(role_ids)
        ).all()
        permission_ids = list(set([m.permission_id for m in mappings]))
        if not permission_ids:
            return []
        return db.query(PermissionModel).filter(
            PermissionModel.id.in_(permission_ids)
        ).all()

    @staticmethod
    def get_user_permission_keys(db: Session, user_id: str) -> List[str]:
        """获取用户的所有权限标识"""
        permissions = UserRoleRepo.get_user_permissions(db, user_id)
        return [p.key for p in permissions]

    @staticmethod
    def is_user_admin(db: Session, user_id: str) -> bool:
        """判断用户是否是管理员（拥有 admin 角色编码）"""
        roles = UserRoleRepo.get_user_roles(db, user_id)
        for role in roles:
            if role.code == "admin":
                return True
        return False
