"""Artifact repository mixin — CRUD and versioning for Artifact/ArtifactVersion.

Composed into ``DatabaseService`` alongside the other repository mixins, so call
sites use the shared ``database_service`` instance. Requires ``self.engine``.
All sync DB work is offloaded to a thread pool via ``asyncio.to_thread``.
"""

import asyncio
import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import List, Optional

from sqlmodel import select

from src.artifact.models.artifact_model import Artifact, ArtifactData, ArtifactVersion
from src.common.logging import logger
from src.common.services.db_session import managed_session


class ArtifactRepositoryMixin:
    """Mixin providing artifact persistence and versioning operations."""

    async def upsert_artifact_version(
        self,
        session_id: str,
        user_id: int,
        identifier: str,
        artifact_type: str,
        title: str,
        content: str,
        message_id: Optional[int] = None,
    ) -> dict:
        """Create a new artifact, or append a new version to an existing one.

        Lookup is by ``(session_id, identifier)``. A new artifact starts at
        version 1; an existing one has ``current_version`` bumped and a fresh
        :class:`ArtifactVersion` appended.

        Returns:
            dict: ``{"artifact_id", "identifier", "version", "version_row_id"}``.
        """

        def _sync() -> dict:
            with managed_session(self.engine) as db:
                art = db.exec(
                    select(Artifact).where(
                        Artifact.session_id == session_id,
                        Artifact.identifier == identifier,
                    )
                ).one_or_none()

                if art is None:
                    art = Artifact(
                        id=str(uuid.uuid4()),
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
                    art.updated_at = datetime.now(UTC)

                db.add(art)
                db.flush()  # ensure art.id is available for the FK

                ver = ArtifactVersion(
                    artifact_id=art.id,
                    version=version,
                    content=content,
                    message_id=message_id,
                )
                db.add(ver)
                db.commit()
                db.refresh(ver)

                logger.info(
                    "artifact_version_saved",
                    artifact_id=art.id,
                    identifier=identifier,
                    version=version,
                    session_id=session_id,
                )
                return {
                    "artifact_id": art.id,
                    "identifier": identifier,
                    "version": version,
                    "version_row_id": ver.id,
                }

        return await asyncio.to_thread(_sync)

    async def set_versions_message_id(self, version_row_ids: List[int], message_id: int) -> None:
        """Back-fill ``message_id`` on versions created during a streaming turn."""
        if not version_row_ids:
            return

        def _sync() -> None:
            with managed_session(self.engine) as db:
                rows = db.exec(
                    select(ArtifactVersion).where(ArtifactVersion.id.in_(version_row_ids))
                ).all()
                for row in rows:
                    row.message_id = message_id
                    db.add(row)
                db.commit()

        await asyncio.to_thread(_sync)

    async def list_session_artifacts(self, session_id: str) -> List[Artifact]:
        """All artifacts for a session, most recently updated first."""

        def _sync() -> List[Artifact]:
            with managed_session(self.engine) as db:
                stmt = (
                    select(Artifact)
                    .where(Artifact.session_id == session_id)
                    .order_by(Artifact.updated_at.desc())
                )
                return list(db.exec(stmt).all())

        return await asyncio.to_thread(_sync)

    async def list_user_artifacts(self, user_id: int) -> List[Artifact]:
        """All artifacts owned by a user, most recently updated first (library)."""

        def _sync() -> List[Artifact]:
            with managed_session(self.engine) as db:
                stmt = (
                    select(Artifact)
                    .where(Artifact.user_id == user_id)
                    .order_by(Artifact.updated_at.desc())
                )
                return list(db.exec(stmt).all())

        return await asyncio.to_thread(_sync)

    async def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Fetch an artifact by id (metadata only)."""

        def _sync() -> Optional[Artifact]:
            with managed_session(self.engine) as db:
                return db.get(Artifact, artifact_id)

        return await asyncio.to_thread(_sync)

    async def get_artifact_version(self, artifact_id: str, version: int) -> Optional[ArtifactVersion]:
        """Fetch a specific version of an artifact."""

        def _sync() -> Optional[ArtifactVersion]:
            with managed_session(self.engine) as db:
                return db.exec(
                    select(ArtifactVersion).where(
                        ArtifactVersion.artifact_id == artifact_id,
                        ArtifactVersion.version == version,
                    )
                ).one_or_none()

        return await asyncio.to_thread(_sync)

    async def get_artifact_versions(self, artifact_id: str) -> List[ArtifactVersion]:
        """All versions of an artifact, newest first."""

        def _sync() -> List[ArtifactVersion]:
            with managed_session(self.engine) as db:
                stmt = (
                    select(ArtifactVersion)
                    .where(ArtifactVersion.artifact_id == artifact_id)
                    .order_by(ArtifactVersion.version.desc())
                )
                return list(db.exec(stmt).all())

        return await asyncio.to_thread(_sync)

    async def publish_artifact(self, artifact_id: str) -> Optional[str]:
        """Mark an artifact public and return its (stable) public token."""

        def _sync() -> Optional[str]:
            with managed_session(self.engine) as db:
                art = db.get(Artifact, artifact_id)
                if art is None:
                    return None
                if not art.public_token:
                    art.public_token = secrets.token_urlsafe(16)
                art.is_published = True
                art.updated_at = datetime.now(UTC)
                db.add(art)
                db.commit()
                logger.info("artifact_published", artifact_id=artifact_id)
                return art.public_token

        return await asyncio.to_thread(_sync)

    async def get_artifact_by_public_token(self, public_token: str) -> Optional[Artifact]:
        """Resolve a published artifact by its public token (metadata only)."""

        def _sync() -> Optional[Artifact]:
            with managed_session(self.engine) as db:
                return db.exec(
                    select(Artifact).where(
                        Artifact.public_token == public_token,
                        Artifact.is_published == True,  # noqa: E712
                    )
                ).one_or_none()

        return await asyncio.to_thread(_sync)

    async def get_artifact_data(self, artifact_id: str) -> dict:
        """Return the stored interactive data for an artifact (``{}`` if none)."""

        def _sync() -> dict:
            with managed_session(self.engine) as db:
                row = db.get(ArtifactData, artifact_id)
                if row is None or not row.data:
                    return {}
                try:
                    return json.loads(row.data)
                except (ValueError, TypeError):
                    return {}

        return await asyncio.to_thread(_sync)

    async def set_artifact_data(self, artifact_id: str, data: dict) -> None:
        """Upsert the interactive data (JSON object) for an artifact."""
        encoded = json.dumps(data, ensure_ascii=False)

        def _sync() -> None:
            with managed_session(self.engine) as db:
                row = db.get(ArtifactData, artifact_id)
                if row is None:
                    row = ArtifactData(artifact_id=artifact_id, data=encoded)
                else:
                    row.data = encoded
                    row.updated_at = datetime.now(UTC)
                db.add(row)
                db.commit()
                logger.info("artifact_data_saved", artifact_id=artifact_id, size=len(encoded))

        await asyncio.to_thread(_sync)

    async def get_public_artifact(self, public_token: str) -> Optional[dict]:
        """Fetch a published artifact's current version by its public token."""

        def _sync() -> Optional[dict]:
            with managed_session(self.engine) as db:
                art = db.exec(
                    select(Artifact).where(
                        Artifact.public_token == public_token,
                        Artifact.is_published == True,  # noqa: E712
                    )
                ).one_or_none()
                if art is None:
                    return None
                ver = db.exec(
                    select(ArtifactVersion).where(
                        ArtifactVersion.artifact_id == art.id,
                        ArtifactVersion.version == art.current_version,
                    )
                ).one_or_none()
                if ver is None:
                    return None
                return {
                    "title": art.title,
                    "artifact_type": art.artifact_type,
                    "content": ver.content,
                    "version": art.current_version,
                }

        return await asyncio.to_thread(_sync)

    async def delete_artifact(self, artifact_id: str) -> bool:
        """Delete a single artifact and its versions. Returns False if not found."""

        def _sync() -> bool:
            with managed_session(self.engine) as db:
                art = db.get(Artifact, artifact_id)
                if art is None:
                    return False
                versions = db.exec(
                    select(ArtifactVersion).where(ArtifactVersion.artifact_id == artifact_id)
                ).all()
                for v in versions:
                    db.delete(v)
                # artifact_data references artifact without ON DELETE CASCADE.
                data = db.get(ArtifactData, artifact_id)
                if data is not None:
                    db.delete(data)
                db.delete(art)
                db.commit()
                logger.info("artifact_deleted", artifact_id=artifact_id)
                return True

        return await asyncio.to_thread(_sync)

    async def delete_session_artifacts(self, session_id: str) -> None:
        """Delete all artifacts (and their versions) for a session."""

        def _sync() -> None:
            with managed_session(self.engine) as db:
                arts = db.exec(select(Artifact).where(Artifact.session_id == session_id)).all()
                for art in arts:
                    versions = db.exec(
                        select(ArtifactVersion).where(ArtifactVersion.artifact_id == art.id)
                    ).all()
                    for v in versions:
                        db.delete(v)
                    # artifact_data references artifact without ON DELETE CASCADE.
                    data = db.get(ArtifactData, art.id)
                    if data is not None:
                        db.delete(data)
                    db.delete(art)
                db.commit()
                logger.info("session_artifacts_deleted", session_id=session_id)

        await asyncio.to_thread(_sync)
