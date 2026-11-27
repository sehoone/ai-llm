"""auth 영속 — 폐기 토큰 블랙리스트 (ADR-0032 Phase 2)."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, delete, select

from src.domains.auth.model import RevokedToken


class RevokedTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def is_revoked(self, jti: str) -> bool:
        return self.session.get(RevokedToken, jti) is not None

    def revoke(self, jti: str, user_id: int, expires_at: datetime) -> None:
        # 멱등 — 이미 폐기된 jti면 재삽입하지 않는다(로그아웃 중복 호출 안전).
        if self.session.get(RevokedToken, jti) is not None:
            return
        self.session.add(RevokedToken(jti=jti, user_id=user_id, expires_at=expires_at))
        self.session.commit()

    def delete_expired(self, now: datetime) -> int:
        """만료 경과 행 삭제(유지보수 스윕). 삭제 건수 반환."""
        result = self.session.exec(delete(RevokedToken).where(RevokedToken.expires_at < now))
        self.session.commit()
        return result.rowcount or 0

    def count(self) -> int:
        return len(list(self.session.exec(select(RevokedToken.jti)).all()))
