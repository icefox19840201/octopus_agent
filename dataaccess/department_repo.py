import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from dataaccess.models import DepartmentModel


class DepartmentRepo:
    """部门数据访问层"""

    @staticmethod
    def create(db: Session, dept_data: Dict[str, Any]) -> DepartmentModel:
        """创建部门"""
        dept = DepartmentModel(
            id=dept_data.get("id", f"dept_{uuid.uuid4().hex[:16]}"),
            name=dept_data["name"],
            code=dept_data["code"],
            parent_id=dept_data.get("parent_id"),
            description=dept_data.get("description"),
            sort_order=dept_data.get("sort_order", 0),
            status=dept_data.get("status", "active"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(dept)
        db.commit()
        db.refresh(dept)
        return dept

    @staticmethod
    def get_by_id(db: Session, dept_id: str) -> Optional[DepartmentModel]:
        """根据ID获取部门"""
        return db.query(DepartmentModel).filter(DepartmentModel.id == dept_id).first()

    @staticmethod
    def get_by_code(db: Session, code: str) -> Optional[DepartmentModel]:
        """根据编码获取部门"""
        return db.query(DepartmentModel).filter(DepartmentModel.code == code).first()

    @staticmethod
    def get_all(db: Session) -> List[DepartmentModel]:
        """获取所有部门"""
        return db.query(DepartmentModel).order_by(DepartmentModel.sort_order).all()

    @staticmethod
    def get_active(db: Session) -> List[DepartmentModel]:
        """获取所有启用的部门"""
        return db.query(DepartmentModel).filter(
            DepartmentModel.status == "active"
        ).order_by(DepartmentModel.sort_order).all()

    @staticmethod
    def get_children(db: Session, parent_id: str) -> List[DepartmentModel]:
        """获取子部门"""
        return db.query(DepartmentModel).filter(
            DepartmentModel.parent_id == parent_id
        ).order_by(DepartmentModel.sort_order).all()

    @staticmethod
    def update(db: Session, dept_id: str, update_data: Dict[str, Any]) -> Optional[DepartmentModel]:
        """更新部门"""
        dept = db.query(DepartmentModel).filter(DepartmentModel.id == dept_id).first()
        if not dept:
            return None
        for key, value in update_data.items():
            if hasattr(dept, key):
                setattr(dept, key, value)
        dept.updated_at = datetime.now()
        db.commit()
        db.refresh(dept)
        return dept

    @staticmethod
    def delete(db: Session, dept_id: str) -> bool:
        """删除部门"""
        dept = db.query(DepartmentModel).filter(DepartmentModel.id == dept_id).first()
        if not dept:
            return False
        db.delete(dept)
        db.commit()
        return True

    @staticmethod
    def count_all(db: Session) -> int:
        """统计部门数量"""
        return db.query(func.count(DepartmentModel.id)).scalar() or 0
