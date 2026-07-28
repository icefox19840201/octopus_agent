from typing import List, Optional, Dict, Any
from dataaccess.database import SessionLocal
from dataaccess.role_repo import RoleRepo, RolePermissionRepo, UserRoleRepo
from dataaccess.models import RoleModel
from utils.logger import logger


class RoleService:
    """角色业务逻辑服务类"""

    @staticmethod
    def _get_session():
        return SessionLocal()

    @staticmethod
    def create_role(role_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建角色"""
        db = RoleService._get_session()
        try:
            # 检查编码是否已存在
            existing = RoleRepo.get_by_code(db, role_data["code"])
            if existing:
                return {"success": False, "message": "角色编码已存在"}

            role = RoleRepo.create(db, role_data)
            return {
                "success": True,
                "data": RoleService._role_to_dict(role),
                "message": "角色创建成功"
            }
        except Exception as e:
            logger.error(f"创建角色失败: {e}")
            return {"success": False, "message": f"创建失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def update_role(role_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新角色"""
        db = RoleService._get_session()
        try:
            role = RoleRepo.get_by_id(db, role_id)
            if not role:
                return {"success": False, "message": "角色不存在"}

            # 检查编码是否与其他角色冲突
            if "code" in update_data:
                existing = RoleRepo.get_by_code(db, update_data["code"])
                if existing and existing.id != role_id:
                    return {"success": False, "message": "角色编码已存在"}

            # 移除permission_ids，单独处理
            permission_ids = update_data.pop("permission_ids", None)

            role = RoleRepo.update(db, role_id, update_data)

            # 更新权限
            if permission_ids is not None:
                RolePermissionRepo.set_role_permissions(db, role_id, permission_ids)

            return {
                "success": True,
                "data": RoleService._role_to_dict(role, db),
                "message": "角色更新成功"
            }
        except Exception as e:
            logger.error(f"更新角色失败: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def delete_role(role_id: str) -> Dict[str, Any]:
        """删除角色"""
        db = RoleService._get_session()
        try:
            success = RoleRepo.delete(db, role_id)
            if success:
                return {"success": True, "message": "角色删除成功"}
            return {"success": False, "message": "角色不存在"}
        except Exception as e:
            logger.error(f"删除角色失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def list_roles() -> List[Dict[str, Any]]:
        """获取所有角色列表"""
        db = RoleService._get_session()
        try:
            roles = RoleRepo.get_all(db)
            return [RoleService._role_to_dict(role, db) for role in roles]
        finally:
            db.close()

    @staticmethod
    def get_role_by_id(role_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取角色详情"""
        db = RoleService._get_session()
        try:
            role = RoleRepo.get_by_id(db, role_id)
            if not role:
                return None
            return RoleService._role_to_dict(role, db)
        finally:
            db.close()

    @staticmethod
    def set_role_permissions(role_id: str, permission_ids: List[str]) -> Dict[str, Any]:
        """设置角色权限"""
        db = RoleService._get_session()
        try:
            role = RoleRepo.get_by_id(db, role_id)
            if not role:
                return {"success": False, "message": "角色不存在"}

            RolePermissionRepo.set_role_permissions(db, role_id, permission_ids)
            return {"success": True, "message": "权限设置成功"}
        except Exception as e:
            logger.error(f"设置角色权限失败: {e}")
            return {"success": False, "message": f"设置失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def get_role_permissions(role_id: str) -> List[Dict[str, Any]]:
        """获取角色的权限列表"""
        db = RoleService._get_session()
        try:
            permissions = RolePermissionRepo.get_role_permissions(db, role_id)
            return [{
                "id": p.id,
                "key": p.key,
                "name": p.name,
                "label": p.label,
                "module": p.module,
                "permission_type": p.permission_type
            } for p in permissions]
        finally:
            db.close()

    @staticmethod
    def _role_to_dict(role: RoleModel, db=None) -> Dict[str, Any]:
        """将角色模型转换为字典"""
        data = {
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "status": role.status,
            "created_at": role.created_at.isoformat() if role.created_at else None,
            "updated_at": role.updated_at.isoformat() if role.updated_at else None
        }

        # 如果提供了db会话，获取权限信息
        if db:
            permission_ids = RolePermissionRepo.get_role_permission_ids(db, role.id)
            data["permission_ids"] = permission_ids

        return data
