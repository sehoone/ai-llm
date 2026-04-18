from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.chatbot.schemas.chat_schema import Message


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    model: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=1, le=16000)
    rag_keys: List[str] = Field(default_factory=list)
    rag_groups: List[str] = Field(default_factory=list)
    rag_search_k: int = Field(default=5, ge=1, le=20)
    rag_enabled: bool = False
    tools_enabled: List[str] = Field(default_factory=list)
    is_published: bool = False


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=16000)
    rag_keys: Optional[List[str]] = None
    rag_groups: Optional[List[str]] = None
    rag_search_k: Optional[int] = Field(default=None, ge=1, le=20)
    rag_enabled: Optional[bool] = None
    tools_enabled: Optional[List[str]] = None
    is_published: Optional[bool] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: Optional[str]
    system_prompt: Optional[str]
    welcome_message: Optional[str]
    model: str
    temperature: float
    max_tokens: int
    rag_keys: List[str]
    rag_groups: List[str]
    rag_search_k: int
    rag_enabled: bool
    tools_enabled: List[str]
    is_published: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentSessionResponse(BaseModel):
    session_id: str
    agent_id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgentChatRequest(BaseModel):
    session_id: str = Field(..., description="에이전트 세션 ID")
    messages: List[Message] = Field(..., min_length=1)
    is_deep_thinking: bool = Field(default=False)


class RagKeyInfo(BaseModel):
    rag_key: str
    rag_group: str
    doc_count: int
    latest_upload: Optional[datetime]


class RagGroupInfo(BaseModel):
    rag_group: str
    key_count: int
    doc_count: int
    latest_upload: Optional[datetime]
