from typing import List, Optional, Dict, Any
from dataaccess.database import SessionLocal
from dataaccess.permission_repo import PermissionRepo
from dataaccess.models import PermissionModel
from utils.logger import logger


class PermissionService:
    """权限业务逻辑服务类"""

    @staticmethod
    def _get_session():
        return SessionLocal()

    @staticmethod
    def create_permission(perm_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建权限"""
        db = PermissionService._get_session()
        try:
            # 检查key是否已存在
            existing = PermissionRepo.get_by_key(db, perm_data["key"])
            if existing:
                return {"success": False, "message": "权限标识已存在"}

            # 处理布尔值转换
            if "is_menu" in perm_data:
                perm_data["is_menu"] = bool(perm_data["is_menu"])
            # 处理状态
            if "status" in perm_data:
                status = perm_data["status"]
                if isinstance(status, bool):
                    perm_data["status"] = "active" if status else "inactive"

            perm = PermissionRepo.create(db, perm_data)
            return {
                "success": True,
                "data": PermissionService._perm_to_dict(perm),
                "message": "权限创建成功"
            }
        except Exception as e:
            logger.error(f"创建权限失败: {e}")
            return {"success": False, "message": f"创建失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def update_permission(perm_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新权限"""
        db = PermissionService._get_session()
        try:
            perm = PermissionRepo.get_by_id(db, perm_id)
            if not perm:
                logger.warning(f"权限不存在: {perm_id}")
                return {"success": False, "message": "权限不存在"}

            logger.info(f"找到权限: id={perm.id}, key={perm.key}, name={perm.name}")
            logger.info(f"更新数据: {update_data}")

            # 检查key是否与其他权限冲突
            if "key" in update_data:
                existing = PermissionRepo.get_by_key(db, update_data["key"])
                if existing and existing.id != perm_id:
                    return {"success": False, "message": "权限标识已存在"}

            # 处理布尔值转换
            if "is_menu" in update_data:
                update_data["is_menu"] = bool(update_data["is_menu"])
            # 处理状态
            if "status" in update_data:
                status = update_data["status"]
                if isinstance(status, bool):
                    update_data["status"] = "active" if status else "inactive"

            perm = PermissionRepo.update(db, perm_id, update_data)
            logger.info(f"更新后权限: id={perm.id}, key={perm.key}, name={perm.name}")
            return {
                "success": True,
                "data": PermissionService._perm_to_dict(perm),
                "message": "权限更新成功"
            }
        except Exception as e:
            logger.error(f"更新权限失败: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def delete_permission(perm_id: str) -> Dict[str, Any]:
        """删除权限"""
        db = PermissionService._get_session()
        try:
            # 检查是否有子权限
            children = PermissionRepo.get_children(db, perm_id)
            if children:
                return {"success": False, "message": "该权限下存在子权限，无法删除"}

            success = PermissionRepo.delete(db, perm_id)
            if success:
                return {"success": True, "message": "权限删除成功"}
            return {"success": False, "message": "权限不存在"}
        except Exception as e:
            logger.error(f"删除权限失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def list_permissions() -> List[Dict[str, Any]]:
        """获取所有权限列表"""
        db = PermissionService._get_session()
        try:
            perms = PermissionRepo.get_all(db)
            return [PermissionService._perm_to_dict(p) for p in perms]
        finally:
            db.close()

    @staticmethod
    def get_permission_list() -> List[Dict[str, Any]]:
        """获取权限列表"""
        db = PermissionService._get_session()
        try:
            all_perms = PermissionRepo.get_active(db)
            return [PermissionService._perm_to_dict(perm) for perm in all_perms]
        finally:
            db.close()

    @staticmethod
    def get_permission_by_id(perm_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取权限"""
        db = PermissionService._get_session()
        try:
            perm = PermissionRepo.get_by_id(db, perm_id)
            if not perm:
                return None
            return PermissionService._perm_to_dict(perm)
        finally:
            db.close()

    @staticmethod
    def get_user_menus(user_permissions: List[str]) -> List[Dict[str, Any]]:
        """根据用户权限获取菜单列表
        
        Args:
            user_permissions: 用户拥有的权限标识列表
            
        Returns:
            菜单列表，按menu_order排序
        """
        db = PermissionService._get_session()
        try:
            # 获取所有菜单权限
            all_menu_perms = PermissionRepo.get_menus(db)
            
            # 过滤用户有权限的菜单
            user_menus = []
            for perm in all_menu_perms:
                if perm.key in user_permissions:
                    user_menus.append({
                        "id": perm.id,
                        "key": perm.key,
                        "name": perm.name,
                        "path": perm.menu_path,
                        "icon": perm.menu_icon,
                        "order": perm.menu_order
                    })
            
            # 按order排序
            user_menus.sort(key=lambda x: x["order"])
            return user_menus
        finally:
            db.close()

    @staticmethod
    def get_modules() -> List[Dict[str, str]]:
        """获取所有模块"""
        db = PermissionService._get_session()
        try:
            return PermissionRepo.get_modules(db)
        finally:
            db.close()

    @staticmethod
    def init_default_permissions() -> Dict[str, Any]:
        """初始化默认权限数据"""
        db = PermissionService._get_session()
        try:
            # 菜单权限列表 - 控制页面菜单显示
            menu_perms = [
                # 仪表盘
                {"key": "menu:dashboard", "name": "仪表盘", "is_menu": True, "menu_path": "dashboard", "menu_icon": "home", "menu_order": 1},
                # Agent管理
                {"key": "menu:agents", "name": "Agent管理", "is_menu": True, "menu_path": "agents", "menu_icon": "bot", "menu_order": 2},
                # Skill管理
                {"key": "menu:skills", "name": "Skill管理", "is_menu": True, "menu_path": "skills", "menu_icon": "tools", "menu_order": 3},
                # MCP管理
                {"key": "menu:mcp", "name": "MCP管理", "is_menu": True, "menu_path": "mcp", "menu_icon": "server", "menu_order": 4},
                # 模型管理
                {"key": "menu:models", "name": "模型管理", "is_menu": True, "menu_path": "models", "menu_icon": "cpu", "menu_order": 5},
                # 权限管控
                {"key": "menu:permission", "name": "权限管控", "is_menu": True, "menu_path": "permission", "menu_icon": "shield", "menu_order": 6},
                # 知识库管理
                {"key": "menu:rag", "name": "知识库管理", "is_menu": True, "menu_path": "rag", "menu_icon": "puzzle", "menu_order": 7},
            ]

            # 功能权限列表 - 控制具体操作
            func_perms = [
                # 系统管理
                {"key": "system:user:view", "name": "查看用户"},
                {"key": "system:user:create", "name": "创建用户"},
                {"key": "system:user:update", "name": "更新用户"},
                {"key": "system:user:delete", "name": "删除用户"},

                {"key": "system:role:view", "name": "查看角色"},
                {"key": "system:role:create", "name": "创建角色"},
                {"key": "system:role:update", "name": "更新角色"},
                {"key": "system:role:delete", "name": "删除角色"},

                {"key": "system:dept:view", "name": "查看部门"},
                {"key": "system:dept:create", "name": "创建部门"},
                {"key": "system:dept:update", "name": "更新部门"},
                {"key": "system:dept:delete", "name": "删除部门"},

                {"key": "system:permission:view", "name": "查看权限"},
                {"key": "system:permission:create", "name": "创建权限"},
                {"key": "system:permission:update", "name": "更新权限"},
                {"key": "system:permission:delete", "name": "删除权限"},

                # Agent管理
                {"key": "agent:view", "name": "查看Agent"},
                {"key": "agent:create", "name": "创建Agent"},
                {"key": "agent:update", "name": "更新Agent"},
                {"key": "agent:delete", "name": "删除Agent"},
                {"key": "agent:chat", "name": "使用Agent"},

                # Skill管理
                {"key": "skill:view", "name": "查看Skill"},
                {"key": "skill:create", "name": "创建Skill"},
                {"key": "skill:update", "name": "更新Skill"},
                {"key": "skill:delete", "name": "删除Skill"},

                # MCP管理
                {"key": "mcp:view", "name": "查看MCP"},
                {"key": "mcp:create", "name": "创建MCP"},
                {"key": "mcp:update", "name": "更新MCP"},
                {"key": "mcp:delete", "name": "删除MCP"},

                # 模型管理
                {"key": "model:view", "name": "查看模型"},
                {"key": "model:create", "name": "创建模型"},
                {"key": "model:update", "name": "更新模型"},
                {"key": "model:delete", "name": "删除模型"},

                # 知识库管理
                {"key": "knowledge:view", "name": "查看知识库"},
                {"key": "knowledge:create", "name": "创建知识库"},
                {"key": "knowledge:update", "name": "更新知识库"},
                {"key": "knowledge:delete", "name": "删除知识库"},
            ]

            default_perms = menu_perms + func_perms

            created_count = 0
            for perm_data in default_perms:
                existing = PermissionRepo.get_by_key(db, perm_data["key"])
                if not existing:
                    PermissionRepo.create(db, perm_data)
                    created_count += 1

            return {
                "success": True,
                "message": f"初始化完成，新增 {created_count} 个权限"
            }
        except Exception as e:
            logger.error(f"初始化权限失败: {e}")
            return {"success": False, "message": f"初始化失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def _perm_to_dict(perm: PermissionModel) -> Dict[str, Any]:
        """将权限模型转换为字典"""
        return {
            "id": perm.id,
            "key": perm.key,
            "name": perm.name,
            "is_menu": perm.is_menu,
            "menu_path": perm.menu_path,
            "menu_icon": perm.menu_icon,
            "menu_order": perm.menu_order,
            "status": perm.status,
            "created_at": perm.created_at.isoformat() if perm.created_at else None
        }
