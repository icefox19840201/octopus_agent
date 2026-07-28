from fastapi import Request, Header
from fastapi.responses import JSONResponse
from typing import Optional
from biziness.department_service import DepartmentService
from biziness.auth_service import AuthService
from utils.logger import logger


def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从请求头中获取token"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


async def create_department(request: Request, authorization: Optional[str] = Header(None)):
    """创建部门"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:dept:create"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        result = DepartmentService.create_department(data)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"创建部门失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def list_departments(authorization: Optional[str] = Header(None)):
    """获取部门列表"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:dept:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        depts = DepartmentService.list_departments()
        return JSONResponse({"success": True, "data": depts})
    except Exception as e:
        logger.error(f"获取部门列表失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_department_tree(authorization: Optional[str] = Header(None)):
    """获取部门树形结构"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:dept:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        tree = DepartmentService.get_department_tree()
        return JSONResponse({"success": True, "data": tree})
    except Exception as e:
        logger.error(f"获取部门树失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_department(dept_id: str, authorization: Optional[str] = Header(None)):
    """获取部门详情"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:dept:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        dept = DepartmentService.get_department_by_id(dept_id)
        if dept:
            return JSONResponse({"success": True, "data": dept})
        return JSONResponse({"success": False, "message": "部门不存在"}, status_code=404)
    except Exception as e:
        logger.error(f"获取部门详情失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def update_department(dept_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """更新部门"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:dept:update"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        result = DepartmentService.update_department(dept_id, data)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"更新部门失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def delete_department(dept_id: str, authorization: Optional[str] = Header(None)):
    """删除部门"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "system:dept:delete"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        result = DepartmentService.delete_department(dept_id)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"删除部门失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
