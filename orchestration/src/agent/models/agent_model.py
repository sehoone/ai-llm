import uuid
from datetime import UTC, datetime
from typing import List, Optional

from sqlalchemy import JSON, Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field

from src.common.models.base import BaseModel


class Agent(BaseModel, table=True):
    __tablename__ = "agent"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: int = Field(index=True)
    name: str = Field(max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None

    model: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)

    rag_keys: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), nullable=False, server_default="{}"))
    rag_groups: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), nullable=False, server_default="{}"))
    rag_search_k: int = Field(default=5)
    rag_enabled: bool = Field(default=False)

    tools_enabled: List[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]"))

    is_published: bool = Field(default=False)
    is_active: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
