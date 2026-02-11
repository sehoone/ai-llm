from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ApiKeyBase(BaseModel):
    name: str = "API Key"
    expires_at: Optional[datetime] = None

class ApiKeyCreate(ApiKeyBase):
    pass

class ApiKeyRead(ApiKeyBase):
    id: int
    user_id: int
    key: str 
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
