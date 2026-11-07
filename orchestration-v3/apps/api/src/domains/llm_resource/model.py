from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


class LlmResource(SQLModel, table=True):
    __tablename__ = "llm_resource"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    name: str
    resource_type: str = Field(default="chat")  # "chat" | "embedding"
    model_name: str | None = Field(default=None)
    provider: str
    api_base: str
    api_key: str
    deployment_name: str | None = Field(default=None)
    api_version: str | None = Field(default=None)
    region: str | None = Field(default=None)
    priority: int = Field(default=0)
    weight: int = Field(default=1)
    is_active: bool = Field(default=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)
