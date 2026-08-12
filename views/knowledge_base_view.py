from fastapi import Request, Header
from fastapi.responses import JSONResponse
from typing import Optional
from biziness.knowledge_base_service import KnowledgeBaseService
from biziness.auth_service import AuthService
from utils.logger import logger
from config.schemas.rag_schemas import Rag_Docs_Path

def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从请求头中获取token"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


async def create_knowledge_base(request: Request, authorization: Optional[str] = Header(None)):
    """创建知识库"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:create"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        user = AuthService.get_current_user(token)
        if not user:
            return JSONResponse({"success": False, "message": "用户不存在"}, status_code=401)

        result = KnowledgeBaseService.create_knowledge_base(
            data,
            user["user_id"],
            user.get("department_id")
        )
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"创建知识库失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def list_knowledge_bases(authorization: Optional[str] = Header(None)):
    """获取知识库列表"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        user = AuthService.get_current_user(token)
        if not user:
            return JSONResponse({"success": False, "message": "用户不存在"}, status_code=401)

        kbs = KnowledgeBaseService.list_knowledge_bases(
            user["user_id"],
            user.get("department_id")
        )
        return JSONResponse({"success": True, "data": kbs})
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_knowledge_base(kb_id: str, authorization: Optional[str] = Header(None)):
    """获取知识库详情"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        user = AuthService.get_current_user(token)
        if not user:
            return JSONResponse({"success": False, "message": "用户不存在"}, status_code=401)

        kb = KnowledgeBaseService.get_knowledge_base(
            kb_id,
            user["user_id"],
            user.get("department_id")
        )
        if kb:
            return JSONResponse({"success": True, "data": kb})
        return JSONResponse({"success": False, "message": "知识库不存在或无权访问"}, status_code=404)
    except Exception as e:
        logger.error(f"获取知识库详情失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def update_knowledge_base(kb_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """更新知识库"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:update"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        user = AuthService.get_current_user(token)
        if not user:
            return JSONResponse({"success": False, "message": "用户不存在"}, status_code=401)

        result = KnowledgeBaseService.update_knowledge_base(kb_id, data, user["user_id"])
        if result["success"]:
            return JSONResponse(result)
        if "无权" in result.get("message", ""):
            return JSONResponse(result, status_code=403)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"更新知识库失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def delete_knowledge_base(kb_id: str, authorization: Optional[str] = Header(None)):
    """删除知识库"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:delete"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        user = AuthService.get_current_user(token)
        if not user:
            return JSONResponse({"success": False, "message": "用户不存在"}, status_code=401)

        result = KnowledgeBaseService.delete_knowledge_base(kb_id, user["user_id"])
        if result["success"]:
            return JSONResponse(result)
        if "无权" in result.get("message", ""):
            return JSONResponse(result, status_code=403)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def create_document(request: Request, authorization: Optional[str] = Header(None)):
    """创建文档"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:create"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        result = KnowledgeBaseService.create_document(data)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"创建文档失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def list_documents(kb_id: str, authorization: Optional[str] = Header(None)):
    """获取文档列表"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        docs = KnowledgeBaseService.list_documents(kb_id)
        return JSONResponse({"success": True, "data": docs})
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def delete_document(doc_id: str, authorization: Optional[str] = Header(None)):
    """删除文档"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:delete"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        result = KnowledgeBaseService.delete_document(doc_id)
        if result["success"]:
            return JSONResponse(result)
        return JSONResponse(result, status_code=400)
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


