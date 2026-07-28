from fastapi import Request, Header
from fastapi.responses import JSONResponse
from typing import Optional
from biziness.permission_service import PermissionService
from biziness.auth_service import AuthService
from utils.logger import logger


def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从请求头中获取token"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


async def create_permission(request: Request, authorization: Optional[str] = Header(None)):
    """创建权限"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:permission:create"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        result = PermissionService.create_permission(data)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"创建权限失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def list_permissions(authorization: Optional[str] = Header(None)):
    """获取权限列表"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:permission:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        perms = PermissionService.list_permissions()
        return JSONResponse({"success": True, "data": perms})
    except Exception as e:
        logger.error(f"获取权限列表失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_permission_list_simple(authorization: Optional[str] = Header(None)):
    """获取权限列表（简化版）"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:permission:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        perms = PermissionService.get_permission_list()
        return JSONResponse({"success": True, "data": perms})
    except Exception as e:
        logger.error(f"获取权限列表失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_user_menus(authorization: Optional[str] = Header(None)):
    """获取当前用户的菜单列表"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    try:
        # 获取当前用户信息
        user = AuthService.get_current_user(token)
        if not user:
            return JSONResponse({"success": False, "message": "用户不存在或token已过期"}, status_code=401)
        
        # 获取用户权限列表
        permissions = user.get("permissions", [])
        roles = user.get("roles", [])
        
        # admin角色拥有所有菜单
        if "admin" in roles:
            # 获取所有菜单
            from dataaccess.database import SessionLocal
            from dataaccess.permission_repo import PermissionRepo
            db = SessionLocal()
            try:
                all_menus = PermissionRepo.get_menus(db)
                menus = [{
                    "id": m.id,
                    "key": m.key,
                    "name": m.name,
                    "path": m.menu_path,
                    "icon": m.menu_icon,
                    "order": m.menu_order
                } for m in all_menus]
                menus.sort(key=lambda x: x["order"])
                return JSONResponse({"success": True, "data": menus})
            finally:
                db.close()
        
        # 普通用户根据权限获取菜单
        menus = PermissionService.get_user_menus(permissions)
        return JSONResponse({"success": True, "data": menus})
    except Exception as e:
        logger.error(f"获取用户菜单失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_permission(perm_id: str, authorization: Optional[str] = Header(None)):
    """获取权限详情"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:permission:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        perm = PermissionService.get_permission_by_id(perm_id)
        if perm:
            return JSONResponse({"success": True, "data": perm})
        return JSONResponse({"success": False, "message": "权限不存在"}, status_code=404)
    except Exception as e:
        logger.error(f"获取权限详情失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def update_permission(perm_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """更新权限"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:permission:update"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        logger.info(f"更新权限请求: perm_id={perm_id}, data={data}")
        result = PermissionService.update_permission(perm_id, data)
        logger.info(f"更新权限结果: {result}")
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"更新权限失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def delete_permission(perm_id: str, authorization: Optional[str] = Header(None)):
    """删除权限"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:permission:delete"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        result = PermissionService.delete_permission(perm_id)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"删除权限失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def init_default_permissions(authorization: Optional[str] = Header(None)):
    """初始化默认权限数据"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:permission:create"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        result = PermissionService.init_default_permissions()
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"初始化权限失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
