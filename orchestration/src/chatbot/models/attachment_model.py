"""Chat attachment model for storing file metadata."""

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ChatAttachment(SQLModel, table=True):
    """File attachment metadata for a chat message.

    The actual file bytes are stored on disk (storage_path).
    This table holds only the metadata needed for listing and downloading.
    """

    __tablename__ = "chat_attachment"

    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="chat_message.id", index=True, nullable=False)
    session_id: str = Field(index=True, nullable=False)
    filename: str = Field(nullable=False)
    content_type: str = Field(nullable=False)
    file_size: int = Field(nullable=False)
    storage_path: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
