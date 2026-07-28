from fastapi import Request, HTTPException, Query
from typing import Optional
from biziness.prompt_service import PromptService
from utils.auth_decorator import require_auth, get_current_user
from utils.logger import logger


@require_auth
async def create_prompt(request: Request):
    """创建提示词"""
    try:
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None
        department_id = user.get('department_id') if user else None

        body = await request.json()
        
        # 验证必填字段
        if not body.get("name"):
            raise HTTPException(status_code=400, detail="提示词名称不能为空")
        if not body.get("content"):
            raise HTTPException(status_code=400, detail="提示词内容不能为空")

        result = PromptService.create_prompt(body, user_id, department_id)
        
        if result.get("success"):
            return {"success": True, "data": result["data"], "message": "创建成功"}
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("创建提示词失败")
        raise HTTPException(status_code=500, detail=str(e))


@require_auth
async def list_prompts(request: Request,
                       page: int = Query(1, ge=1),
                       page_size: int = Query(10, ge=1, le=100),
                       keyword: Optional[str] = None,
                       is_active: Optional[bool] = None):
    """获取提示词列表"""
    try:
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None
        department_id = user.get('department_id') if user else None

        result = PromptService.list_prompts(
            user_id=user_id,
            department_id=department_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            is_active=is_active
        )
        
        if result.get("success"):
            return {"success": True, "data": result["data"], "message": "获取列表成功"}
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "获取失败"))
    except Exception as e:
        logger.exception("获取提示词列表失败")
        raise HTTPException(status_code=500, detail=str(e))


@require_auth
async def get_prompt(request: Request, prompt_id: str):
    """获取提示词详情"""
    try:
        result = PromptService.get_prompt(prompt_id)
        
        if result.get("success"):
            return {"success": True, "data": result["data"], "message": "获取成功"}
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "提示词不存在"))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取提示词详情失败: prompt_id={prompt_id}")
        raise HTTPException(status_code=500, detail=str(e))


@require_auth
async def get_prompt_by_key(request: Request, key: str):
    """通过key获取提示词"""
    try:
        result = PromptService.get_prompt_by_key(key)
        
        if result.get("success"):
            return {"success": True, "data": result["data"], "message": "获取成功"}
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "提示词不存在"))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取提示词失败: key={key}")
        raise HTTPException(status_code=500, detail=str(e))


@require_auth
async def update_prompt(request: Request, prompt_id: str):
    """更新提示词"""
    try:
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None

        body = await request.json()
        
        result = PromptService.update_prompt(prompt_id, body, user_id)
        
        if result.get("success"):
            return {"success": True, "data": result["data"], "message": "更新成功"}
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"更新提示词失败: prompt_id={prompt_id}")
        raise HTTPException(status_code=500, detail=str(e))


@require_auth
async def delete_prompt(request: Request, prompt_id: str):
    """删除提示词"""
    try:
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None

        result = PromptService.delete_prompt(prompt_id, user_id)

        if result.get("success"):
            return {"success": True, "message": "删除成功"}
        else:
            return {"success": False, "message": result.get("error", "删除失败")}
    except Exception as e:
        logger.exception(f"删除提示词失败: prompt_id={prompt_id}")
        return {"success": False, "message": str(e)}
