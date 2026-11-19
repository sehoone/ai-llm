"""connector 도메인 테이블 (ADR-0022). schema: llmonl.

- `connector`: 사내 MCP 서버 등록(사용자별). 도구 로드·위험도는 engine/agent가, 등록·인가는
  domain이 소유한다(ADR-0005 경계). `sk-` 키는 평문이 아니라 참조(`credential_ref`)로 보관.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


class Connector(SQLModel, table=True):
    __tablename__ = "connector"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: int = Field(index=True)
    name: str
    description: str | None = Field(default=None)
    mcp_url: str = Field(default="")
    credential_ref: str | None = Field(default=None)
    enabled: bool = Field(default=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)
