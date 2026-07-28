import uuid
import re
from typing import List, Dict, Any, Optional
from dataaccess.database import SessionLocal
from dataaccess.prompt_repo import PromptRepo
from dataaccess.role_repo import UserRoleRepo
from dataaccess.models import PromptModel, AgentModel
from utils.pagination import PageResult, paginate
from utils.logger import logger


class PromptService:
    """
    提示词管理服务类
    """

    @staticmethod
    def _get_session():
        return SessionLocal()

    @staticmethod
    def extract_variables(content: str) -> List[str]:
        """从提示词内容中提取变量，如 {{variable}} 或 {variable}"""
        # 匹配 {{variable}} 和 {variable} 格式
        pattern = r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}|\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.findall(pattern, content)
        # 提取非空的分组
        variables = []
        for match in matches:
            var = match[0] if match[0] else match[1]
            if var and var not in variables:
                variables.append(var)
        return variables

    @staticmethod
    def render_prompt(content: str, variables: Dict[str, Any]) -> str:
        """渲染提示词，替换变量"""
        result = content
        for key, value in variables.items():
            # 替换 {{variable}} 和 {variable} 两种格式
            result = result.replace(f'{{{{{key}}}}}', str(value))
            result = result.replace(f'{{{key}}}', str(value))
        return result

    @classmethod
    def create_prompt(cls, prompt_data: Dict[str, Any], user_id: str, department_id: str = None) -> Dict[str, Any]:
        """创建提示词"""
        db = cls._get_session()
        try:
            # 验证必填字段
            name = prompt_data.get("name", "").strip()
            content = prompt_data.get("content", "").strip()
            
            if not name:
                return {"success": False, "error": "提示词名称不能为空"}
            if not content:
                return {"success": False, "error": "提示词内容不能为空"}

            # 构建数据
            data = {
                "id": str(uuid.uuid4()),
                "name": name,
                "content": content,
                "description": prompt_data.get("description", "").strip(),
                "is_active": prompt_data.get("is_active", True),
                "type": prompt_data.get("type", "private"),
                "created_by": user_id,
                "department_id": department_id
            }

            prompt = PromptRepo.create(db, data)
            return {
                "success": True,
                "data": cls._prompt_to_dict(prompt)
            }
        except Exception as e:
            logger.error(f"创建提示词失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @classmethod
    def update_prompt(cls, prompt_id: str, update_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """更新提示词"""
        db = cls._get_session()
        try:
            prompt = PromptRepo.get_by_id(db, prompt_id)
            if not prompt:
                return {"success": False, "error": "提示词不存在"}

            # 检查权限（只有创建者或管理员可以修改）
            if prompt.created_by != user_id:
                # TODO: 检查是否是管理员
                return {"success": False, "error": "无权修改此提示词"}

            # 过滤不允许修改的字段
            allowed_fields = ["name", "content", "description", "is_active", "type"]
            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

            updated = PromptRepo.update(db, prompt_id, filtered_data)
            if updated:
                return {
                    "success": True,
                    "data": cls._prompt_to_dict(updated)
                }
            return {"success": False, "error": "更新失败"}
        except Exception as e:
            logger.error(f"更新提示词失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @classmethod
    def delete_prompt(cls, prompt_id: str, user_id: str) -> Dict[str, Any]:
        """删除提示词"""
        db = cls._get_session()
        try:
            prompt = PromptRepo.get_by_id(db, prompt_id)
            if not prompt:
                return {"success": False, "error": "提示词不存在"}

            # 权限检查：只有创建者或管理员可以删除
            if user_id:
                is_admin = UserRoleRepo.is_user_admin(db, user_id)
                if prompt.created_by != user_id and not is_admin:
                    return {"success": False, "error": "无权删除，仅本人或管理员可以删除"}

            # 检查是否有智能体引用该提示词
            agent_count = db.query(AgentModel).filter(AgentModel.prompt_id == prompt_id).count()
            if agent_count > 0:
                return {"success": False, "error": f"当前提示词已有智能体引用，请先解除引用后再删除"}

            success = PromptRepo.delete(db, prompt_id)
            return {"success": success}
        except Exception as e:
            logger.error(f"删除提示词失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @classmethod
    def get_prompt(cls, prompt_id: str) -> Dict[str, Any]:
        """获取单个提示词详情"""
        db = cls._get_session()
        try:
            prompt = PromptRepo.get_by_id(db, prompt_id)
            if not prompt:
                return {"success": False, "error": "提示词不存在"}
            return {
                "success": True,
                "data": cls._prompt_to_dict(prompt)
            }
        except Exception as e:
            logger.error(f"获取提示词失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @classmethod
    def list_prompts(cls, user_id: str, department_id: str = None, 
                     page: int = 1, page_size: int = 10,
                     keyword: str = None,
                     is_active: bool = None) -> Dict[str, Any]:
        """获取提示词列表（分页）"""
        db = cls._get_session()
        try:
            offset = (page - 1) * page_size
            prompts = PromptRepo.get_visible_prompts_paginated(
                db, user_id, department_id, offset, page_size, keyword, is_active
            )
            total = PromptRepo.count_visible_prompts(db, user_id, department_id, keyword, is_active)

            items = [cls._prompt_to_dict(p) for p in prompts]
            return {
                "success": True,
                "data": {
                    "items": items,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
        except Exception as e:
            logger.error(f"获取提示词列表失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @classmethod
    def render_prompt_by_id(cls, prompt_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """通过ID渲染提示词"""
        db = cls._get_session()
        try:
            prompt = PromptRepo.get_by_id(db, prompt_id)
            if not prompt:
                return {"success": False, "error": "提示词不存在"}
            
            if not prompt.is_active:
                return {"success": False, "error": "提示词未启用"}

            rendered = cls.render_prompt(prompt.content, variables)
            return {
                "success": True,
                "data": {
                    "id": prompt.id,
                    "name": prompt.name,
                    "rendered_content": rendered
                }
            }
        except Exception as e:
            logger.error(f"渲染提示词失败: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @staticmethod
    def _prompt_to_dict(prompt: PromptModel) -> Dict[str, Any]:
        """将PromptModel转换为字典"""
        return {
            "id": prompt.id,
            "name": prompt.name,
            "content": prompt.content,
            "description": prompt.description,
            "is_active": prompt.is_active,
            "type": prompt.type,
            "created_by": prompt.created_by,
            "department_id": prompt.department_id,
            "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
            "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None
        }
