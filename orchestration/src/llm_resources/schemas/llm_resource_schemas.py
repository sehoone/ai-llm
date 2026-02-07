from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class LLMResourceBase(BaseModel):
    name: str
    provider: str
    api_base: str
    api_key: str
    deployment_name: Optional[str] = None
    api_version: Optional[str] = None
    region: Optional[str] = None
    priority: int = 0
    is_active: bool = True

class LLMResourceCreate(LLMResourceBase):
    pass

class LLMResourceUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    deployment_name: Optional[str] = None
    api_version: Optional[str] = None
    region: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

class LLMResourceResponse(LLMResourceBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
