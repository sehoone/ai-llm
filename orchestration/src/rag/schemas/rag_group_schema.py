from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RagGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=300)
    color: str = Field(default="#6366f1")


class RagGroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=300)
    color: Optional[str] = None


class RagGroupResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: Optional[str]
    color: str
    key_count: int = 0
    doc_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class RagKeyCreate(BaseModel):
    rag_key: str = Field(min_length=1, max_length=200)
    rag_group: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=300)
    rag_type: str = Field(default="chatbot_shared")


class RagKeyUpdate(BaseModel):
    rag_group: Optional[str] = None
    description: Optional[str] = None
    rag_type: Optional[str] = None


class RagKeyResponse(BaseModel):
    id: str
    user_id: int
    rag_key: str
    rag_group: str
    description: Optional[str]
    rag_type: str
    doc_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True
