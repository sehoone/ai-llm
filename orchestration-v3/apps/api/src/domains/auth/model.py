from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


class RevokedToken(SQLModel, table=True):
    """폐기된 JWT jti 블랙리스트 (ADR-0032 Phase 2) — 로그아웃 시 등록, 만료 전까지 인증 차단.

    만료 경과 행은 유지보수 스윕이 삭제한다(만료 토큰은 decode에서 이미 거부되므로 보관 의미 없음).
    """

    __tablename__ = "revoked_token"
    __table_args__ = {"schema": "llmonl"}

    jti: str = Field(primary_key=True, max_length=64)
    user_id: int = Field(index=True)
    expires_at: NaiveDatetime
    revoked_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
