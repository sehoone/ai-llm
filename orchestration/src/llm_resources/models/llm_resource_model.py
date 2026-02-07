from typing import Optional
from sqlmodel import Field
from src.common.models.base import BaseModel

class LLMResource(BaseModel, table=True):
    __tablename__ = "llm_resource"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    provider: str
    api_base: str
    api_key: str
    deployment_name: Optional[str] = None
    api_version: Optional[str] = None
    region: Optional[str] = None
    priority: int = Field(default=0)
    is_active: bool = Field(default=True)
