import uuid
from typing import Optional

from sqlmodel import Field, UniqueConstraint

from src.common.models.base import BaseModel


class RagGroupConfig(BaseModel, table=True):
    __tablename__ = "rag_group_config"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_rag_group_user_name"),)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: int = Field(index=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    color: str = Field(default="#6366f1")
