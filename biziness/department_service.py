from typing import List, Optional, Dict, Any
from dataaccess.database import SessionLocal
from dataaccess.department_repo import DepartmentRepo
from dataaccess.models import DepartmentModel
from utils.logger import logger


class DepartmentService:
    """部门业务逻辑服务类"""

    @staticmethod
    def _get_session():
        return SessionLocal()

    @staticmethod
    def create_department(dept_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建部门"""
        db = DepartmentService._get_session()
        try:
            # 检查编码是否已存在
            existing = DepartmentRepo.get_by_code(db, dept_data["code"])
            if existing:
                return {"success": False, "message": "部门编码已存在"}

            dept = DepartmentRepo.create(db, dept_data)
            return {
                "success": True,
                "data": DepartmentService._dept_to_dict(dept),
                "message": "部门创建成功"
            }
        except Exception as e:
            logger.error(f"创建部门失败: {e}")
            return {"success": False, "message": f"创建失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def update_department(dept_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新部门"""
        db = DepartmentService._get_session()
        try:
            dept = DepartmentRepo.get_by_id(db, dept_id)
            if not dept:
                return {"success": False, "message": "部门不存在"}

            # 检查编码是否与其他部门冲突
            if "code" in update_data:
                existing = DepartmentRepo.get_by_code(db, update_data["code"])
                if existing and existing.id != dept_id:
                    return {"success": False, "message": "部门编码已存在"}

            dept = DepartmentRepo.update(db, dept_id, update_data)
            return {
                "success": True,
                "data": DepartmentService._dept_to_dict(dept),
                "message": "部门更新成功"
            }
        except Exception as e:
            logger.error(f"更新部门失败: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def delete_department(dept_id: str) -> Dict[str, Any]:
        """删除部门"""
        db = DepartmentService._get_session()
        try:
            # 检查是否有子部门
            children = DepartmentRepo.get_children(db, dept_id)
            if children:
                return {"success": False, "message": "该部门下存在子部门，无法删除"}

            success = DepartmentRepo.delete(db, dept_id)
            if success:
                return {"success": True, "message": "部门删除成功"}
            return {"success": False, "message": "部门不存在"}
        except Exception as e:
            logger.error(f"删除部门失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}
        finally:
            db.close()

    @staticmethod
    def get_department_tree() -> List[Dict[str, Any]]:
        """获取部门树形结构"""
        db = DepartmentService._get_session()
        try:
            all_depts = DepartmentRepo.get_active(db)
            return DepartmentService._build_tree(all_depts)
        finally:
            db.close()

    @staticmethod
    def list_departments() -> List[Dict[str, Any]]:
        """获取所有部门列表"""
        db = DepartmentService._get_session()
        try:
            depts = DepartmentRepo.get_all(db)
            return [DepartmentService._dept_to_dict(d) for d in depts]
        finally:
            db.close()

    @staticmethod
    def get_department_by_id(dept_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取部门"""
        db = DepartmentService._get_session()
        try:
            dept = DepartmentRepo.get_by_id(db, dept_id)
            if not dept:
                return None
            return DepartmentService._dept_to_dict(dept)
        finally:
            db.close()

    @staticmethod
    def _build_tree(depts: List[DepartmentModel], parent_id: str = None) -> List[Dict[str, Any]]:
        """构建部门树"""
        tree = []
        for dept in depts:
            if dept.parent_id == parent_id:
                node = DepartmentService._dept_to_dict(dept)
                children = DepartmentService._build_tree(depts, dept.id)
                if children:
                    node["children"] = children
                tree.append(node)
        return tree

    @staticmethod
    def _dept_to_dict(dept: DepartmentModel) -> Dict[str, Any]:
        """将部门模型转换为字典"""
        return {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "parent_id": dept.parent_id,
            "description": dept.description,
            "sort_order": dept.sort_order,
            "status": dept.status,
            "created_at": dept.created_at.isoformat() if dept.created_at else None,
            "updated_at": dept.updated_at.isoformat() if dept.updated_at else None
        }
