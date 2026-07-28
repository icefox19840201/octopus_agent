from typing import Any, Dict, List, Optional


class PageResult:
    """通用分页结果"""

    def __init__(self, items: list, total: int, page: int, page_size: int):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages
        }


def paginate(page: Optional[int], page_size: Optional[int]) -> tuple:
    """规范化分页参数，返回 (offset, limit)
    
    Args:
        page: 页码，从1开始，默认1
        page_size: 每页条数，默认10
        
    Returns:
        (offset, limit) 元组
    """
    if page is None or page < 1:
        page = 1
    if page_size is None or page_size < 1:
        page_size = 10
    return (page - 1) * page_size, page_size
