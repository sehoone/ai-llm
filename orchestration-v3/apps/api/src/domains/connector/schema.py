"""connector 도메인 DTO (ADR-0022). 비스트림 응답은 라우터에서 `ApiResponse[T]`로 감싼다.

보안: `credential_ref`(sk- 키 참조)는 응답에 포함 여부만 bool로 노출하고 값은 반환하지 않는다.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domains.connector.model import Connector


class ConnectorCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    mcp_url: str = Field(min_length=1)
    credential_ref: str | None = None
    enabled: bool = True


class ConnectorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    mcp_url: str | None = Field(default=None, min_length=1)
    credential_ref: str | None = None
    enabled: bool | None = None


class ConnectorResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: str | None
    mcp_url: str
    has_credential: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime | None

    @classmethod
    def from_model(cls, c: Connector) -> "ConnectorResponse":
        return cls(
            id=c.id,
            user_id=c.user_id,
            name=c.name,
            description=c.description,
            mcp_url=c.mcp_url,
            has_credential=bool(c.credential_ref),
            enabled=c.enabled,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )


class ConnectorToolItem(BaseModel):
    """로드된 MCP 도구 미리보기 — 이름·설명·위험 티어."""

    name: str
    description: str
    risk: str
