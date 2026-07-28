import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
from dataaccess.models_repo import LLMModelRepo
from dataaccess.models import LLMModel
from biziness.llm import test_llm_connection


class ModelService:
    """模型管理服务类"""

    @staticmethod
    async def create_model(db: Session, request) -> Dict[str, Any]:
        """创建模型配置"""
        try:
            data = await request.json()
            if not data:
                raise HTTPException(status_code=400, detail="请求体不能为空")

            # 获取当前用户ID
            user_id = request.session.get('user_id')

            # 生成唯一ID
            model_id = str(uuid.uuid4()).replace('-', '')[:32]

            # 准备数据
            model_data = {
                'id': model_id,
                'name': data.get('name', ''),
                'model_type': data.get('modelType', 'chat'),
                'provider': data.get('provider', 'openai'),
                'model_name': data.get('modelName', ''),
                'base_url': data.get('baseUrl', ''),
                'api_key': data.get('apiKey', ''),
                'description': data.get('description', ''),
                'status': 'stopped'
            }

            # 创建模型
            model = LLMModelRepo.create(db, model_data)
            return {"code": 200, "message": "创建成功", "data": ModelService._model_to_dict(model)}
        except HTTPException:
            raise
        except Exception as e:
            return {"code": 500, "message": f"创建失败: {str(e)}"}

    @staticmethod
    def get_model(db: Session, model_id: str) -> Dict[str, Any]:
        """获取模型详情"""
        try:
            model = LLMModelRepo.get_by_id(db, model_id)
            if not model:
                raise HTTPException(status_code=404, detail="模型不存在")
            return {"code": 200, "message": "获取成功", "data": ModelService._model_to_dict(model)}
        except HTTPException:
            raise
        except Exception as e:
            return {"code": 500, "message": f"获取失败: {str(e)}"}

    @staticmethod
    def list_models(db: Session, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """获取模型列表（分页）"""
        try:
            page_result = LLMModelRepo.get_page(db, page, page_size)
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "items": [ModelService._model_to_dict(m) for m in page_result.items],
                    "total": page_result.total,
                    "page": page_result.page,
                    "page_size": page_result.page_size,
                    "total_pages": page_result.total_pages
                }
            }
        except Exception as e:
            return {"code": 500, "message": f"获取失败: {str(e)}"}

    @staticmethod
    async def update_model(db: Session, request, model_id: str) -> Dict[str, Any]:
        """更新模型配置"""
        try:
            data = await request.json()
            if not data:
                raise HTTPException(status_code=400, detail="请求体不能为空")

            # 准备更新数据
            update_data = {}
            if 'name' in data:
                update_data['name'] = data['name']
            if 'modelType' in data:
                update_data['model_type'] = data['modelType']
            if 'provider' in data:
                update_data['provider'] = data['provider']
            if 'modelName' in data:
                update_data['model_name'] = data['modelName']
            if 'baseUrl' in data:
                update_data['base_url'] = data['baseUrl']
            if 'apiKey' in data:
                update_data['api_key'] = data['apiKey']
            if 'description' in data:
                update_data['description'] = data['description']
            model = LLMModelRepo.update(db, model_id, update_data)
            if not model:
                raise HTTPException(status_code=404, detail="模型不存在")
            return {"code": 200, "message": "更新成功", "data": ModelService._model_to_dict(model)}
        except HTTPException:
            raise
        except Exception as e:
            return {"code": 500, "message": f"更新失败: {str(e)}"}

    @staticmethod
    def delete_model(db: Session, model_id: str) -> Dict[str, Any]:
        """删除模型配置"""
        try:
            success = LLMModelRepo.delete(db, model_id)
            if not success:
                raise HTTPException(status_code=404, detail="模型不存在")
            return {"code": 200, "message": "删除成功"}
        except HTTPException:
            raise
        except Exception as e:
            return {"code": 500, "message": f"删除失败: {str(e)}"}

    @staticmethod
    def test_model_connection(db: Session, model_id: str) -> Dict[str, Any]:
        """测试模型连接"""
        try:
            model = LLMModelRepo.get_by_id(db, model_id)
            if not model:
                raise HTTPException(status_code=404, detail="模型不存在")
            
            # 测试连接
            success, message = test_llm_connection(
                model_name=model.model_name,
                base_url=model.base_url,
                api_key=model.api_key
            )
            
            # 更新状态
            new_status = 'active' if success else 'stopped'
            LLMModelRepo.update(db, model_id, {'status': new_status})
            
            return {
                "code": 200 if success else 400,
                "message": message,
                "data": {"status": new_status, "connected": success}
            }
        except HTTPException:
            raise
        except Exception as e:
            # 更新状态为 stopped
            try:
                LLMModelRepo.update(db, model_id, {'status': 'stopped'})
            except:
                pass
            return {"code": 500, "message": f"测试失败: {str(e)}"}

    @staticmethod
    def _model_to_dict(model: LLMModel) -> Dict[str, Any]:
        """将模型对象转换为字典"""
        return {
            'id': model.id,
            'name': model.name,
            'modelType': model.model_type,
            'provider': model.provider,
            'modelName': model.model_name,
            'baseUrl': model.base_url,
            'apiKey': model.api_key,
            'description': model.description,
            'status': model.status or 'stopped',
            'createdAt': model.created_at.strftime('%Y-%m-%d') if model.created_at else None,
            'updatedAt': model.updated_at.strftime('%Y-%m-%d %H:%M:%S') if model.updated_at else None
        }
