from pydantic import BaseModel
from typing import List, Dict, Any, Optional
class SkillCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    code: Optional[str] = ""
    skill_space: Optional[str] = "private"

class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = None