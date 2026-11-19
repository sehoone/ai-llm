"""artifact 도메인 서비스 (ADR-0013). 영속·인가. 수집(버전 업서트)은 chat 스트림이 호출(3b)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlmodel import Session

from src.domains.artifact.model import Artifact
from src.domains.artifact.repository import ArtifactRepository
from src.domains.user.model import User, UserRole

# 사용자가 직접 만든 standalone 아티팩트는 chat 세션에 속하지 않는다(세션 0 센티넬).
STANDALONE_SESSION_ID = 0


class ArtifactService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = ArtifactRepository(session)

    # ── 생성 ──
    def create(self, user: User, title: str, artifact_type: str, content: str) -> Artifact:
        """사용자가 직접 만든 standalone 아티팩트(세션 0). v1 버전으로 저장."""
        identifier = f"user-{uuid.uuid4().hex[:12]}"
        result = self.repo.upsert_version(
            session_id=STANDALONE_SESSION_ID,
            user_id=user.id,
            identifier=identifier,
            artifact_type=artifact_type,
            title=title,
            content=content,
        )
        art = self.repo.get_artifact(result["artifact_id"])
        if art is None:  # pragma: no cover - 방금 생성했으므로 발생하지 않음
            raise HTTPException(status_code=500, detail="Failed to create artifact")
        return art

    # ── 조회 ──
    def list_artifacts(self, user: User, session_id: int | None) -> list[Artifact]:
        if session_id is not None:
            arts = self.repo.list_session_artifacts(session_id)
            if user.role in (UserRole.ADMIN, UserRole.SUPERADMIN):
                return arts
            return [a for a in arts if a.user_id == user.id]
        return self.repo.list_user_artifacts(user.id)

    def get_detail(self, user: User, artifact_id: str) -> tuple[Artifact, str]:
        art = self._owned(artifact_id, user)
        return art, self._current_content(art)

    def list_versions(self, user: User, artifact_id: str):
        self._owned(artifact_id, user)
        return self.repo.list_versions(artifact_id)

    def get_version(self, user: User, artifact_id: str, version: int):
        self._owned(artifact_id, user)
        ver = self.repo.get_version(artifact_id, version)
        if ver is None:
            raise HTTPException(status_code=404, detail="Artifact version not found")
        return ver

    def delete(self, user: User, artifact_id: str) -> None:
        art = self._owned(artifact_id, user)
        self.repo.delete_artifact(art)

    # ── 공개 ──
    def publish(self, user: User, artifact_id: str) -> str:
        art = self._owned(artifact_id, user)
        return self.repo.publish(art)

    def get_public(self, public_token: str) -> dict | None:
        art = self.repo.get_by_public_token(public_token)
        if art is None:
            return None
        ver = self.repo.get_version(art.id, art.current_version)
        if ver is None:
            return None
        return {
            "title": art.title,
            "artifact_type": art.artifact_type,
            "content": ver.content,
            "version": art.current_version,
        }

    # ── 인터랙티브 데이터 ──
    def get_data(self, user: User, artifact_id: str) -> dict:
        self._owned(artifact_id, user)
        return self.repo.get_data(artifact_id)

    def set_data(self, user: User, artifact_id: str, data: dict) -> None:
        self._owned(artifact_id, user)
        self.repo.set_data(artifact_id, data)

    def get_public_data(self, public_token: str) -> dict | None:
        art = self.repo.get_by_public_token(public_token)
        if art is None:
            return None
        return self.repo.get_data(art.id)

    def set_public_data(self, public_token: str, data: dict) -> bool:
        art = self.repo.get_by_public_token(public_token)
        if art is None:
            return False
        self.repo.set_data(art.id, data)
        return True

    # ── 내부 ──
    def _current_content(self, art: Artifact) -> str:
        ver = self.repo.get_version(art.id, art.current_version)
        return ver.content if ver else ""

    def _owned(self, artifact_id: str, user: User) -> Artifact:
        art = self.repo.get_artifact(artifact_id)
        if art is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        if art.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(status_code=403, detail="Not your artifact")
        return art
