"""artifact 도메인 영속 계층 (ADR-0013). V2 ArtifactRepositoryMixin을 동기 세션으로 이식."""

from __future__ import annotations

import json
import secrets
from datetime import datetime

from sqlmodel import Session, select

from src.domains.artifact.model import Artifact, ArtifactData, ArtifactVersion


class ArtifactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── 수집(버전 업서트) ──
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
        """(session_id, identifier)로 조회해 신규면 v1, 기존이면 current_version+1 버전 추가."""
        art = self.session.exec(
            select(Artifact).where(
                Artifact.session_id == session_id, Artifact.identifier == identifier
            )
        ).one_or_none()

        if art is None:
            art = Artifact(
                session_id=session_id,
                user_id=user_id,
                identifier=identifier,
                artifact_type=artifact_type,
                title=title,
                current_version=1,
            )
            version = 1
        else:
            version = art.current_version + 1
            art.current_version = version
            if title:
                art.title = title
            if artifact_type:
                art.artifact_type = artifact_type
            art.updated_at = datetime.utcnow()

        self.session.add(art)
        self.session.flush()  # art.id 확보

        ver = ArtifactVersion(artifact_id=art.id, version=version, content=content, message_id=message_id)
        self.session.add(ver)
        self.session.commit()
        self.session.refresh(ver)
        return {"artifact_id": art.id, "identifier": identifier, "version": version, "version_row_id": ver.id}

    def set_versions_message_id(self, version_row_ids: list[int], message_id: int) -> None:
        if not version_row_ids:
            return
        rows = self.session.exec(
            select(ArtifactVersion).where(ArtifactVersion.id.in_(version_row_ids))
        ).all()
        for row in rows:
            row.message_id = message_id
            self.session.add(row)
        self.session.commit()

    # ── 조회 ──
    def list_session_artifacts(self, session_id: int) -> list[Artifact]:
        return list(
            self.session.exec(
                select(Artifact).where(Artifact.session_id == session_id).order_by(Artifact.updated_at.desc())
            ).all()
        )

    def list_user_artifacts(self, user_id: int) -> list[Artifact]:
        return list(
            self.session.exec(
                select(Artifact).where(Artifact.user_id == user_id).order_by(Artifact.updated_at.desc())
            ).all()
        )

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        return self.session.get(Artifact, artifact_id)

    def get_version(self, artifact_id: str, version: int) -> ArtifactVersion | None:
        return self.session.exec(
            select(ArtifactVersion).where(
                ArtifactVersion.artifact_id == artifact_id, ArtifactVersion.version == version
            )
        ).one_or_none()

    def list_versions(self, artifact_id: str) -> list[ArtifactVersion]:
        return list(
            self.session.exec(
                select(ArtifactVersion)
                .where(ArtifactVersion.artifact_id == artifact_id)
                .order_by(ArtifactVersion.version.desc())
            ).all()
        )

    # ── 공개 ──
    def publish(self, art: Artifact) -> str:
        if not art.public_token:
            art.public_token = secrets.token_urlsafe(16)
        art.is_published = True
        art.updated_at = datetime.utcnow()
        self.session.add(art)
        self.session.commit()
        return art.public_token

    def get_by_public_token(self, public_token: str) -> Artifact | None:
        return self.session.exec(
            select(Artifact).where(
                Artifact.public_token == public_token, Artifact.is_published == True  # noqa: E712
            )
        ).one_or_none()

    # ── 인터랙티브 데이터 ──
    def get_data(self, artifact_id: str) -> dict:
        row = self.session.get(ArtifactData, artifact_id)
        if row is None or not row.data:
            return {}
        try:
            return json.loads(row.data)
        except (ValueError, TypeError):
            return {}

    def set_data(self, artifact_id: str, data: dict) -> None:
        encoded = json.dumps(data, ensure_ascii=False)
        row = self.session.get(ArtifactData, artifact_id)
        if row is None:
            row = ArtifactData(artifact_id=artifact_id, data=encoded)
        else:
            row.data = encoded
            row.updated_at = datetime.utcnow()
        self.session.add(row)
        self.session.commit()

    # ── 삭제 ──
    def delete_artifact(self, art: Artifact) -> None:
        for v in self.session.exec(
            select(ArtifactVersion).where(ArtifactVersion.artifact_id == art.id)
        ).all():
            self.session.delete(v)
        data = self.session.get(ArtifactData, art.id)
        if data is not None:
            self.session.delete(data)
        self.session.delete(art)
        self.session.commit()

    def delete_session_artifacts(self, session_id: int) -> None:
        for art in self.list_session_artifacts(session_id):
            self.delete_artifact(art)
