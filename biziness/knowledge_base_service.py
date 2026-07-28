from typing import List, Optional, Dict, Any
from dataaccess.database import SessionLocal
from dataaccess.knowledge_base_repo import KnowledgeBaseRepo, KnowledgeDocumentRepo
from dataaccess.role_repo import UserRoleRepo
from dataaccess.models import KnowledgeBaseModel
from utils.logger import logger


class KnowledgeBaseService:
    """知识库业务逻辑服务类"""

    @staticmethod
    def _get_session():
        return SessionLocal()

    @staticmethod
    def _kb_to_dict(kb: KnowledgeBaseModel) -> Dict[str, Any]:
        """将知识库模型转换为字典"""
        return {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "embedding_model": kb.embedding_model,
            "vector_store_path": kb.vector_store_path,
            "type": kb.type,
            "created_by": kb.created_by,
            "department_id": kb.department_id,
            "status": kb.status,
            "created_at": kb.created_at.isoformat() if kb.created_at else None,
            "updated_at": kb.updated_at.isoformat() if kb.updated_at else None,
            "creator_name": kb.creator.username if kb.creator else None,
            "department_name": kb.department.name if kb.department else None
        }

    @staticmethod
    def _doc_to_dict(doc) -> Dict[str, Any]:
        """将文档模型转换为字典"""
        return {
            "id": doc.id,
            "kb_id": doc.kb_id,
            "title": doc.title,
            "content": doc.content,
            "file_path": doc.file_path,
            "file_type": doc.file_type,
            "chunk_count": doc.chunk_count,
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
        }

    @staticmethod
    def create_knowledge_base(kb_data: Dict[str, Any], user_id: str, department_id: Optional[str] = None) -> Dict[str, Any]:
        """创建知识库"""
        db = KnowledgeBaseService._get_session()
        try:
            kb_data["created_by"] = user_id
            if department_id:
                kb_data["department_id"] = department_id

            kb = KnowledgeBaseRepo.create(db, kb_data)
            return {
                "success": True,
                "data": KnowledgeBaseService._kb_to_dict(kb),
                "message": "知识库创建成功"
            }
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
            return {"success": False, "message": f"创建失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def list_knowledge_bases(user_id: str, department_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取用户可见的知识库列表"""
        db = KnowledgeBaseService._get_session()
        try:
            is_admin = UserRoleRepo.is_user_admin(db, user_id)
            kbs = KnowledgeBaseRepo.get_visible_knowledge_bases(db, user_id, department_id, is_admin)
            return [KnowledgeBaseService._kb_to_dict(kb) for kb in kbs]
        finally:
            db.close()

    @staticmethod
    def get_knowledge_base(kb_id: str, user_id: str, department_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取知识库详情"""
        db = KnowledgeBaseService._get_session()
        try:
            kb = KnowledgeBaseRepo.get_by_id(db, kb_id)
            if not kb:
                return None

            # 检查权限
            is_admin = UserRoleRepo.is_user_admin(db, user_id)
            if not is_admin and kb.created_by != user_id:
                if kb.type == "private":
                    return None
                elif kb.type == "group" and kb.department_id != department_id:
                    return None

            return KnowledgeBaseService._kb_to_dict(kb)
        finally:
            db.close()

    @staticmethod
    def update_knowledge_base(kb_id: str, update_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """更新知识库"""
        db = KnowledgeBaseService._get_session()
        try:
            kb = KnowledgeBaseRepo.get_by_id(db, kb_id)
            if not kb:
                return {"success": False, "message": "知识库不存在"}

            # 检查权限
            is_admin = UserRoleRepo.is_user_admin(db, user_id)
            if kb.created_by != user_id and not is_admin:
                return {"success": False, "message": "无权修改，仅本人或管理员可以修改"}

            kb = KnowledgeBaseRepo.update(db, kb_id, update_data)
            return {
                "success": True,
                "data": KnowledgeBaseService._kb_to_dict(kb),
                "message": "知识库更新成功"
            }
        except Exception as e:
            logger.error(f"更新知识库失败: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def delete_knowledge_base(kb_id: str, user_id: str) -> Dict[str, Any]:
        """删除知识库"""
        db = KnowledgeBaseService._get_session()
        try:
            kb = KnowledgeBaseRepo.get_by_id(db, kb_id)
            if not kb:
                return {"success": False, "message": "知识库不存在"}

            # 检查权限
            is_admin = UserRoleRepo.is_user_admin(db, user_id)
            if kb.created_by != user_id and not is_admin:
                return {"success": False, "message": "无权删除，仅本人或管理员可以删除"}

            success = KnowledgeBaseRepo.delete(db, kb_id)
            if success:
                return {"success": True, "message": "知识库删除成功"}
            return {"success": False, "message": "删除失败"}
        except Exception as e:
            logger.error(f"删除知识库失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def create_document(doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建文档"""
        db = KnowledgeBaseService._get_session()
        try:
            doc = KnowledgeDocumentRepo.create(db, doc_data)
            return {
                "success": True,
                "data": KnowledgeBaseService._doc_to_dict(doc),
                "message": "文档创建成功"
            }
        except Exception as e:
            logger.error(f"创建文档失败: {e}")
            return {"success": False, "message": f"创建失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def list_documents(kb_id: str) -> List[Dict[str, Any]]:
        """获取知识库下的文档列表"""
        db = KnowledgeBaseService._get_session()
        try:
            docs = KnowledgeDocumentRepo.get_by_kb_id(db, kb_id)
            return [KnowledgeBaseService._doc_to_dict(doc) for doc in docs]
        finally:
            db.close()

    @staticmethod
    def delete_document(doc_id: str) -> Dict[str, Any]:
        """删除文档"""
        db = KnowledgeBaseService._get_session()
        try:
            success = KnowledgeDocumentRepo.delete(db, doc_id)
            if success:
                return {"success": True, "message": "文档删除成功"}
            return {"success": False, "message": "文档不存在"}
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}
        finally:
            db.close()
