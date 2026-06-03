import uuid
from typing import Optional

from sqlmodel import Field, UniqueConstraint

from src.common.models.base import BaseModel


class RagKeyConfig(BaseModel, table=True):
    __tablename__ = "rag_key_config"
    __table_args__ = (UniqueConstraint("user_id", "rag_key", name="uq_rag_key_user"),)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: int = Field(index=True)
    rag_key: str = Field(index=True)
    rag_group: str = Field(index=True)
    description: Optional[str] = None
    rag_type: str = Field(default="chatbot_shared")
