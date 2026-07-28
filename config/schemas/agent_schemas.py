from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class AgentCreateRequest(BaseModel):
    """创建Agent请求模型"""
    name: str
    description: str = ""
    skills: List[str] = []
    config: Dict[str, Any] = {}


class AgentUpdateRequest(BaseModel):
    """更新Agent请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[List[str]] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None