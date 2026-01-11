from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ChatHistoryResponse(BaseModel):
    id: int
    session_id: str
    user_email: str
    question: str
    answer: str
    created_at: datetime
    session_name: Optional[str] = None
