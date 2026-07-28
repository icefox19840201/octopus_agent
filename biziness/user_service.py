import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataaccess.database import SessionLocal
from dataaccess.user_repo import UserRepo
from dataaccess.role_repo import UserRoleRepo
from dataaccess.models import UserModel
from utils.logger import logger


class UserService:
    """用户业务逻辑服务类"""

    @staticmethod
    def _get_session():
        return SessionLocal()

    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建用户"""
        db = UserService._get_session()
        try:
            # 检查用户名是否已存在
            existing = UserRepo.get_by_username(db, user_data["username"])
            if existing:
                return {"success": False, "message": "用户名已存在"}

            # 哈希密码
            password_hash = UserRepo.hash_password(user_data["password"])

            # 创建用户
            user = UserRepo.create(db, {
                "username": user_data["username"],
                "email": user_data.get("email"),
                "password_hash": password_hash,
                "real_name": user_data.get("real_name"),
                "phone": user_data.get("phone"),
                "department_id": user_data.get("department_id"),
                "status": user_data.get("status", "active")
            })

            # 设置角色
            if "role_ids" in user_data and user_data["role_ids"]:
                UserRoleRepo.set_user_roles(db, user.id, user_data["role_ids"])

            return {
                "success": True,
                "data": UserService._user_to_dict(user),
                "message": "用户创建成功"
            }
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return {"success": False, "message": f"创建失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def update_user(user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户"""
        db = UserService._get_session()
        try:
            user = UserRepo.get_by_id(db, user_id)
            if not user:
                return {"success": False, "message": "用户不存在"}

            # 更新密码
            if "password" in update_data and update_data["password"]:
                update_data["password_hash"] = UserRepo.hash_password(update_data["password"])
                del update_data["password"]

            # 移除role_ids，单独处理
            role_ids = update_data.pop("role_ids", None)

            # 更新用户基本信息
            user = UserRepo.update(db, user_id, update_data)

            # 更新角色
            if role_ids is not None:
                UserRoleRepo.set_user_roles(db, user_id, role_ids)

            return {
                "success": True,
                "data": UserService._user_to_dict(user),
                "message": "用户更新成功"
            }
        except Exception as e:
            logger.error(f"更新用户失败: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def delete_user(user_id: str) -> Dict[str, Any]:
        """删除用户"""
        db = UserService._get_session()
        try:
            success = UserRepo.delete(db, user_id)
            if success:
                return {"success": True, "message": "用户删除成功"}
            return {"success": False, "message": "用户不存在"}
        except Exception as e:
            logger.error(f"删除用户失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取用户详情"""
        db = UserService._get_session()
        try:
            user = UserRepo.get_by_id(db, user_id)
            if not user:
                return None
            return UserService._user_to_dict(user, db)
        finally:
            db.close()

    @staticmethod
    def list_users() -> List[Dict[str, Any]]:
        """获取所有用户列表"""
        db = UserService._get_session()
        try:
            users = UserRepo.get_all(db)
            return [UserService._user_to_dict(user, db) for user in users]
        finally:
            db.close()

    @staticmethod
    def get_user_permissions(user_id: str) -> List[str]:
        """获取用户的所有权限标识"""
        db = UserService._get_session()
        try:
            return UserRoleRepo.get_user_permission_keys(db, user_id)
        finally:
            db.close()

    @staticmethod
    def get_user_roles(user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有角色"""
        db = UserService._get_session()
        try:
            roles = UserRoleRepo.get_user_roles(db, user_id)
            return [{"id": r.id, "name": r.name, "code": r.code} for r in roles]
        finally:
            db.close()

    @staticmethod
    def _user_to_dict(user: UserModel, db=None) -> Dict[str, Any]:
        """将用户模型转换为字典"""
        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "real_name": user.real_name,
            "phone": user.phone,
            "department_id": user.department_id,
            "department_name": user.department.name if user.department else None,
            "status": user.status,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }

        # 如果提供了db会话，获取角色信息
        if db:
            role_ids = UserRoleRepo.get_user_role_ids(db, user.id)
            data["role_ids"] = role_ids
            roles = UserRoleRepo.get_user_roles(db, user.id)
            data["roles"] = [{"id": r.id, "name": r.name, "code": r.code} for r in roles]

        return data
