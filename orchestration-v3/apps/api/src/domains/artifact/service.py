"""artifact 도메인 서비스 (ADR-0013). 영속·인가. 수집(버전 업서트)은 chat 스트림이 호출(3b)."""

from __future__ import annotations

from sqlmodel import Session

from src.core.exceptions import NotFoundError
from src.domains.artifact.model import Artifact
from src.domains.artifact.repository import ArtifactRepository
from src.platform.authz import assert_owner_or_admin
from src.platform.user.model import User, UserRole


class ArtifactService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = ArtifactRepository(session)

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
            raise NotFoundError("Artifact version not found")
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
            raise NotFoundError("Artifact not found")
        assert_owner_or_admin(user, art.user_id, message="Not your artifact")
        return art
