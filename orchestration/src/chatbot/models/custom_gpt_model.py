import uuid
from typing import Optional
from sqlmodel import Field
from src.common.models.base import BaseModel

class CustomGPT(BaseModel, table=True):
    __tablename__ = "custom_gpt"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: int = Field(index=True)
    name: str
    description: Optional[str] = None
    instructions: str
    rag_key: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True)
    is_public: bool = False
    model: str = "gpt-4-turbo"
