from typing import List, Optional
from pydantic import BaseModel, Field

from src.chatbot.schemas.chat_schema import Message


class CustomGPTCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    instructions: str
    is_public: bool = False
    model: str = "gpt-4-turbo"
    rag_key: Optional[str] = None

class CustomGPTUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    instructions: Optional[str] = None
    is_public: Optional[bool] = None
    model: Optional[str] = None

class CustomGPTResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: Optional[str]
    instructions: str
    rag_key: str
    is_public: bool
    model: str

    class Config:
        from_attributes = True


class GPTSessionResponse(BaseModel):
    session_id: str
    name: str
    custom_gpt_id: str

    class Config:
        from_attributes = True


class GPTChatRequest(BaseModel):
    session_id: str = Field(..., description="GPT 세션 ID")
    is_deep_thinking: bool = Field(default=False)
    messages: List[Message] = Field(..., min_length=1)
