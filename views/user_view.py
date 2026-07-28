from fastapi import Request, Header
from fastapi.responses import JSONResponse
from typing import Optional
from biziness.user_service import UserService
from biziness.auth_service import AuthService
from utils.logger import logger


def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从请求头中获取token"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def check_permission(token: str, permission: str) -> bool:
    """检查权限"""
    return AuthService.check_permission(token, permission)


async def create_user(request: Request, authorization: Optional[str] = Header(None)):
    """创建用户"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not check_permission(token, "system:user:create"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        result = UserService.create_user(data)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def list_users(authorization: Optional[str] = Header(None)):
    """获取用户列表"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not check_permission(token, "system:user:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        users = UserService.list_users()
        return JSONResponse({"success": True, "data": users})
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_user(user_id: str, authorization: Optional[str] = Header(None)):
    """获取用户详情"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not check_permission(token, "system:user:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        user = UserService.get_user_by_id(user_id)
        if user:
            return JSONResponse({"success": True, "data": user})
        return JSONResponse({"success": False, "message": "用户不存在"}, status_code=404)
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def update_user(user_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """更新用户"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not check_permission(token, "system:user:update"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        result = UserService.update_user(user_id, data)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def delete_user(user_id: str, authorization: Optional[str] = Header(None)):
    """删除用户"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not check_permission(token, "system:user:delete"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        result = UserService.delete_user(user_id)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_user_roles(user_id: str, authorization: Optional[str] = Header(None)):
    """获取用户的角色"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not check_permission(token, "system:user:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        roles = UserService.get_user_roles(user_id)
        return JSONResponse({"success": True, "data": roles})
    except Exception as e:
        logger.error(f"获取用户角色失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_user_permissions(user_id: str, authorization: Optional[str] = Header(None)):
    """获取用户的权限"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not check_permission(token, "system:user:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        permissions = UserService.get_user_permissions(user_id)
        return JSONResponse({"success": True, "data": permissions})
    except Exception as e:
        logger.error(f"获取用户权限失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
