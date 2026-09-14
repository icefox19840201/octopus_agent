from fastapi import Request, Header
from fastapi.responses import JSONResponse
from typing import Optional
from biziness.rag_service import RagService
from biziness.auth_service import AuthService
from biziness.redis_mq import get_kb_queue_tasks
from utils.logger import logger


def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从请求头中获取token"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


async def hit_test(kb_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """知识库命中测试：根据问题检索知识库，返回匹配的文档片段"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        data = await request.json()
        question = (data.get("question") or "").strip()
        if not question:
            return JSONResponse({"success": False, "message": "测试问题不能为空"}, status_code=400)

        user = AuthService.get_current_user(token)
        if not user:
            return JSONResponse({"success": False, "message": "用户不存在"}, status_code=401)

        results = RagService.hit_test(
          query=question,kb_id=kb_id
        )
        logger.info(f"知识库 {kb_id} 命中测试完成，返回 {len(results)} 条结果")
        return JSONResponse({"success": True, "data": {"kb_id": kb_id, "count": len(results), "results": results}})
    except Exception as e:
        logger.error(f"知识库命中测试失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


async def get_kb_queue(kb_id: str, authorization: Optional[str] = Header(None)):
    """获取指定知识库在 redis 队列中排队中的上传任务信息"""
    token = get_token_from_header(authorization)
    if not token:
        return JSONResponse({"success": False, "message": "未提供认证token"}, status_code=401)

    if not AuthService.check_permission(token, "knowledge:view"):
        return JSONResponse({"success": False, "message": "没有权限执行此操作"}, status_code=403)

    try:
        user = AuthService.get_current_user(token)
        if not user:
            return JSONResponse({"success": False, "message": "用户不存在"}, status_code=401)

        tasks = get_kb_queue_tasks(kb_id)
        logger.info(f"[知识库队列] 用户 {user['user_id']} 查询知识库 {kb_id} 排队信息，排队任务数={len(tasks)}")
        return JSONResponse({
            "success": True,
            "data": {
                "kb_id": kb_id,
                "count": len(tasks),
                "tasks": tasks
            }
        })
    except Exception as e:
        logger.error(f"获取知识库排队信息失败: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
