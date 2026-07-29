from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session
from dataaccess.database import get_db
from biziness.model_service import ModelService
from dataaccess.models import LLMModel
from utils.logger import logger

async def create_model(request: Request, db: Session = Depends(get_db)):
    """创建模型配置"""
    return await ModelService.create_model(db, request)


async def list_models(request: Request, db: Session = Depends(get_db)):
    """获取模型列表（分页）"""
    # 从查询参数中获取分页参数
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    return ModelService.list_models(db, page, page_size)


async def get_model(request: Request, model_id: str, db: Session = Depends(get_db)):
    """获取模型详情"""
    return ModelService.get_model(db, model_id)


async def update_model(request: Request, model_id: str, db: Session = Depends(get_db)):
    """更新模型配置"""
    return await ModelService.update_model(db, request, model_id)


async def delete_model(request: Request, model_id: str, db: Session = Depends(get_db)):
    """删除模型配置"""
    return ModelService.delete_model(db, model_id)


async def test_model_connection(request: Request, model_id: str, db: Session = Depends(get_db)):
    """测试模型连接"""
    return ModelService.test_model_connection(db, model_id)


async def get_active_models(request: Request, db: Session = Depends(get_db)):
    """获取可用模型列表（用于Agent配置选择）"""
    try:
        # 获取所有模型（不限制状态，让用户可以选择任何已配置的模型）
        models = db.query(LLMModel).all()
        models_list = []
        
        for model in models:
            models_list.append({
                'id': model.id,
                'name': model.name,
                'model_name': model.model_name,
                'provider': model.provider,
                'description': model.description,
                'status': model.status
            })
        
        return {"code": 200, "message": "获取成功", "data": {"models": models_list, "count": len(models_list)}}
    except Exception as e:
        logger.exception(f"获取可用模型列表失败: {e}")
        return {"code": 500, "message": f"获取失败: {str(e)}"}
