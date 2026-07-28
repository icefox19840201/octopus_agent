from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class UploadedFile(BaseModel):
    """上传文件信息"""
    name: str
    path: str
    size: int


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    agent_id: str = "default"
    conversation_id: Optional[str] = None
    files: Optional[List[UploadedFile]] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    skills_used: List[str] = []
    conversation_id: str = ""