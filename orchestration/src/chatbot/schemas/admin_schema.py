from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from src.chatbot.schemas.chat_schema import AttachmentMeta


class ChatHistoryResponse(BaseModel):
    id: int
    session_id: str
    user_email: str
    question: str
    answer: str
    created_at: datetime
    session_name: Optional[str] = None
    attachments: List[AttachmentMeta] = []


class ChatHistoryListResponse(BaseModel):
    items: List[ChatHistoryResponse]
    total: int
