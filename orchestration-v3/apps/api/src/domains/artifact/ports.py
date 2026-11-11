"""artifact 공개 포트 — 타 도메인이 버전·발행 인프라를 재사용하는 유일한 진입점 (ADR-0013).

chat·meeting이 스트리밍 산출물/회의록 발행에 아티팩트 버전·공개링크 인프라를 공유한다.
내부 `repository`/`model`은 캡슐화 — 외부 도메인은 이 포트로만 접근한다(import-linter 강제).
인가는 호출 도메인이 끝낸 뒤 호출한다(포트는 소유권을 재검증하지 않는다).
"""

from __future__ import annotations

from sqlmodel import Session

from src.domains.artifact.model import Artifact
from src.domains.artifact.repository import ArtifactRepository


class ArtifactIngest:
    """아티팩트 수집·발행 인프라 공개 포트."""

    def __init__(self, session: Session) -> None:
        self._repo = ArtifactRepository(session)

    def upsert_version(
        self,
        *,
        session_id: int,
        user_id: int,
        identifier: str,
        artifact_type: str,
        title: str,
        content: str,
        message_id: int | None = None,
    ) -> dict:
        """(session_id, identifier) 기준 버전 업서트. 신규면 v1, 기존이면 current+1."""
        return self._repo.upsert_version(
            session_id=session_id,
            user_id=user_id,
            identifier=identifier,
            artifact_type=artifact_type,
            title=title,
            content=content,
            message_id=message_id,
        )

    def link_versions_to_message(self, version_row_ids: list[int], message_id: int) -> None:
        """이번 턴에 생성된 버전 행들을 assistant 메시지에 연결."""
        self._repo.set_versions_message_id(version_row_ids, message_id)

    def get(self, artifact_id: str) -> Artifact | None:
        return self._repo.get_artifact(artifact_id)

    def delete(self, artifact: Artifact) -> None:
        self._repo.delete_artifact(artifact)

    def publish(self, artifact: Artifact) -> str:
        """공개 토큰 발급 + 발행. 토큰을 반환."""
        return self._repo.publish(artifact)
