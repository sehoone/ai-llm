import uuid

from sqlmodel import Field

from src.common.models.base import BaseModel


class AgentSession(BaseModel, table=True):
    __tablename__ = "agent_session"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    agent_id: str = Field(index=True)
    user_id: int = Field(index=True)
    name: str = Field(default="")
