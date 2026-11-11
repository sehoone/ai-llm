from datetime import datetime

from pydantic import BaseModel, Field

from src.platform.api_key.model import ApiKey


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime

    @classmethod
    def full(cls, k: ApiKey) -> "ApiKeyResponse":
        """생성 시 1회만 전체 키 노출."""
        return cls(
            id=k.id, name=k.name, key=k.key, is_active=k.is_active,
            expires_at=k.expires_at, created_at=k.created_at,
        )

    @classmethod
    def masked(cls, k: ApiKey) -> "ApiKeyResponse":
        """목록 조회용 — key 마스킹."""
        return cls(
            id=k.id, name=k.name, key=k.key[:8] + "****", is_active=k.is_active,
            expires_at=k.expires_at, created_at=k.created_at,
        )
