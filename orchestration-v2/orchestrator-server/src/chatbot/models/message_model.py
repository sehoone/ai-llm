"""This file contains the message model for the application."""

from datetime import (
    UTC,
    datetime,
)
from typing import Optional

from sqlmodel import (
    Field,
    SQLModel,
)


class ChatMessage(SQLModel, table=True):
    """Message model for storing chat messages.

    Attributes:
        id: The primary key
        session_id: The session ID this message belongs to
        question: The user's question
        answer: The assistant's answer
        created_at: When the message was created
    """

    __tablename__ = "chat_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, foreign_key="session.id")
    question: str = Field(nullable=False)
    answer: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
