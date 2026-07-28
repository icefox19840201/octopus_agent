from fastapi import Request, Header
from fastapi.responses import JSONResponse
from typing import Optional
from biziness.role_service import RoleService
from biziness.auth_service import AuthService
from utils.logger import logger


def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从请求头中获取token"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


async def create_role(request: Request, authorization: Optional[str] = Header(None)):
    """创建角色"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:role:create"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        result = RoleService.create_role(data)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"创建角色失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def list_roles(authorization: Optional[str] = Header(None)):
    """获取角色列表"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:role:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        roles = RoleService.list_roles()
        return JSONResponse({"success": True, "data": roles})
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_role(role_id: str, authorization: Optional[str] = Header(None)):
    """获取角色详情"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:role:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        role = RoleService.get_role_by_id(role_id)
        if role:
            return JSONResponse({"success": True, "data": role})
        return JSONResponse({"success": False, "message": "角色不存在"}, status_code=404)
    except Exception as e:
        logger.error(f"获取角色详情失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def update_role(role_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """更新角色"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:role:update"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        result = RoleService.update_role(role_id, data)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"更新角色失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def delete_role(role_id: str, authorization: Optional[str] = Header(None)):
    """删除角色"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:role:delete"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        result = RoleService.delete_role(role_id)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"删除角色失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_role_permissions(role_id: str, authorization: Optional[str] = Header(None)):
    """获取角色的权限"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:role:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        permissions = RoleService.get_role_permissions(role_id)
        return JSONResponse({"success": True, "data": permissions})
    except Exception as e:
        logger.error(f"获取角色权限失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def set_role_permissions(role_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """设置角色权限"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:role:update"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        permission_ids = data.get("permission_ids", [])
        result = RoleService.set_role_permissions(role_id, permission_ids)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"设置角色权限失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
