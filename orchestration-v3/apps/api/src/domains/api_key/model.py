from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_key"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    key: str = Field(unique=True)
    name: str = Field(default="API Key")
    expires_at: NaiveDatetime | None = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)

    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at < datetime.utcnow()
