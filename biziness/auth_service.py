import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import jwt, JWTError, ExpiredSignatureError
from dataaccess.database import SessionLocal
from dataaccess.user_repo import UserRepo
from dataaccess.role_repo import UserRoleRepo
from utils.logger import logger
from settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS


class AuthService:
    """认证业务逻辑服务类 - JWT实现"""

    @staticmethod
    def _get_session():
        return SessionLocal()

    @staticmethod
    def _generate_token(user_data: Dict[str, Any]) -> str:
        """生成JWT token"""
        expire = datetime.now() + timedelta(hours=JWT_EXPIRE_HOURS)
        payload = {
            "user_id": user_data.get("user_id", ""),
            "username": user_data["username"],
            "roles": user_data.get("roles", []),  # 角色列表
            "permissions": user_data.get("permissions", []),  # 权限列表
            "email": user_data.get("email", ""),
            "department_id": user_data.get("department_id"),  # 部门ID
            "exp": expire,
            "iat": datetime.now(),
            "jti": str(uuid.uuid4())  # JWT ID，用于唯一标识token
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token

    @staticmethod
    def _decode_token(token: str) -> Optional[Dict[str, Any]]:
        """解码JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except ExpiredSignatureError:
            logger.warning("JWT token已过期")
            return None
        except JWTError as e:
            logger.warning(f"JWT token无效: {e}")
            return None

    @staticmethod
    def login(username: str, password: str) -> Dict[str, Any]:
        """用户登录

        Args:
            username: 用户名
            password: 原始密码

        Returns:
            包含登录结果的字典
        """
        db = AuthService._get_session()
        try:
            user = UserRepo.get_by_username(db, username)
            if not user:
                logger.warning(f"登录失败: 用户不存在, username={username}")
                return {
                    "success": False,
                    "error_code": "INVALID_CREDENTIALS",
                    "message": "用户名或密码错误"
                }

            if user.status != "active":
                logger.warning(f"登录失败: 账户已停用, username={username}")
                return {
                    "success": False,
                    "error_code": "ACCOUNT_DISABLED",
                    "message": "该账户已被停用"
                }

            if not UserRepo.verify_password(password, user.password_hash):
                logger.warning(f"登录失败: 密码错误, username={username}")
                return {
                    "success": False,
                    "error_code": "INVALID_CREDENTIALS",
                    "message": "用户名或密码错误"
                }

            # 获取用户的角色和权限
            roles = UserRoleRepo.get_user_roles(db, user.id)
            role_codes = [r.code for r in roles]
            permissions = UserRoleRepo.get_user_permission_keys(db, user.id)

            # 生成JWT token
            user_data = {
                "user_id": user.id,
                "username": user.username,
                "roles": role_codes,
                "permissions": permissions,
                "email": user.email,
                "department_id": user.department_id
            }
            token = AuthService._generate_token(user_data)

            logger.info(f"登录成功: username={username}, roles={role_codes}")
            return {
                "success": True,
                "data": {
                    "token": token,
                    "user_id": user.id,
                    "username": user.username,
                    "roles": [{"id": r.id, "name": r.name, "code": r.code} for r in roles],
                    "permissions": permissions,
                    "email": user.email,
                    "expires_in": JWT_EXPIRE_HOURS * 3600  # 过期时间（秒）
                },
                "message": "登录成功"
            }
        except Exception as e:
            logger.exception(f"登录过程发生异常, username={username}")
            return {
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": "登录失败，服务器内部错误"
            }
        finally:
            db.close()

    @staticmethod
    def logout(token: str) -> Dict[str, Any]:
        """用户登出

        Args:
            token: 用户token

        Returns:
            包含登出结果的字典
        """
        # JWT是无状态的，登出只需要客户端删除token
        # 如果需要强制失效token，可以使用黑名单（Redis等）
        return {
            "success": True,
            "message": "已退出登录"
        }

    @staticmethod
    def verify(token: str) -> Dict[str, Any]:
        """验证token有效性

        Args:
            token: 用户token

        Returns:
            包含验证结果的字典
        """
        if not token:
            return {
                "success": False,
                "authenticated": False
            }

        payload = AuthService._decode_token(token)
        if not payload:
            return {
                "success": False,
                "authenticated": False
            }

        return {
            "success": True,
            "authenticated": True,
            "data": {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "email": payload.get("email"),
                "department_id": payload.get("department_id")
            }
        }

    @staticmethod
    def get_current_user(token: str) -> Optional[Dict[str, Any]]:
        """获取当前用户信息

        Args:
            token: 用户token

        Returns:
            用户信息字典，如果token无效则返回None
        """
        if not token:
            return None

        payload = AuthService._decode_token(token)
        if not payload:
            return None

        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", []),
            "email": payload.get("email")
        }

    @staticmethod
    def check_permission(token: str, required_permission: str) -> bool:
        """检查用户是否有指定权限

        Args:
            token: 用户token
            required_permission: 需要的权限标识

        Returns:
            是否有权限
        """
        user = AuthService.get_current_user(token)
        if not user:
            return False

        roles = user.get("roles", [])
        # 管理员拥有所有权限
        if "admin" in roles:
            return True

        permissions = user.get("permissions", [])
        # 支持通配符匹配，如 "system:user:*" 匹配 "system:user:view"
        for perm in permissions:
            if perm == required_permission or (perm.endswith(":*") and required_permission.startswith(perm[:-2])):
                return True

        return False

    @staticmethod
    def check_role(token: str, required_role: str) -> bool:
        """检查用户是否有指定角色

        Args:
            token: 用户token
            required_role: 需要的角色编码

        Returns:
            是否有角色
        """
        user = AuthService.get_current_user(token)
        if not user:
            return False

        roles = user.get("roles", [])
        return required_role in roles

    @staticmethod
    def change_password(token: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码

        Args:
            token: 用户token
            old_password: 原密码
            new_password: 新密码

        Returns:
            包含修改结果的字典
        """
        # 验证token
        payload = AuthService._decode_token(token)
        if not payload:
            return {
                "success": False,
                "message": "登录已过期，请重新登录"
            }

        if len(new_password) < 6:
            return {
                "success": False,
                "message": "新密码长度至少6位"
            }

        db = AuthService._get_session()
        try:
            user = UserRepo.get_by_username(db, payload["username"])
            if not user:
                return {
                    "success": False,
                    "message": "用户不存在"
                }

            if not UserRepo.verify_password(old_password, user.password_hash):
                return {
                    "success": False,
                    "message": "原密码错误"
                }

            new_hash = UserRepo.hash_password(new_password)
            user.password_hash = new_hash
            db.commit()

            logger.info(f"密码修改成功: username={user.username}")
            return {
                "success": True,
                "message": "密码修改成功"
            }
        except Exception as e:
            logger.exception(f"修改密码失败: username={payload.get('username')}")
            return {
                "success": False,
                "message": "修改密码失败，服务器内部错误"
            }
        finally:
            db.close()
