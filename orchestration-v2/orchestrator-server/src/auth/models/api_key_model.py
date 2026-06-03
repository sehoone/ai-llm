from typing import Optional
from datetime import datetime
from sqlmodel import Field
from src.common.models.base import BaseModel

class ApiKey(BaseModel, table=True):
    __tablename__ = "api_key"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    key: str = Field(unique=True, index=True)
    name: str = Field(default="API Key")
    expires_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
