"""Meeting orchestration + persistence.

Owns the meeting lifecycle (create → transcribe → summarize → complete) and all
DB access for the module. DB work uses the shared engine via ``managed_session``
and is offloaded with ``asyncio.to_thread`` — the same pattern as the artifact
repository. Artifact publishing reuses ``database_service`` helpers.
"""

import asyncio
import json
import os
import uuid
from datetime import UTC, datetime
from typing import Dict, List, Optional

from sqlmodel import select

from src.common.config import settings
from src.common.logging import logger
from src.common.services.database import database_service
from src.common.services.db_session import managed_session
from src.meeting_minutes.models.meeting_model import (
    Meeting,
    MeetingMinutes,
    MeetingSegment,
    MeetingStatus,
)
from src.meeting_minutes.services.minutes_service import minutes_service
from src.meeting_minutes.services.storage_service import storage_service
from src.meeting_minutes.services.transcription_service import transcription_service


class MeetingService:
    """Business logic and persistence for meeting minutes."""

    @property
    def engine(self):
        """Shared SQLAlchemy engine (read lazily from the DB service singleton)."""
        return database_service.engine

    # ── CRUD ────────────────────────────────────────────────────────────────

    async def create_meeting(
        self, user_id: int, title: str, object_key: str, filename: str, language: str
    ) -> Meeting:
        def _sync() -> Meeting:
            with managed_session(self.engine) as db:
                meeting = Meeting(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    title=title,
                    status=MeetingStatus.UPLOADED,
                    audio_object_key=object_key,
                    audio_filename=filename,
                    language=language,
                )
                db.add(meeting)
                db.commit()
                db.refresh(meeting)
                return meeting

        return await asyncio.to_thread(_sync)

    async def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        def _sync() -> Optional[Meeting]:
            with managed_session(self.engine) as db:
                return db.get(Meeting, meeting_id)

        return await asyncio.to_thread(_sync)

    async def list_meetings(self, user_id: int) -> List[Meeting]:
        def _sync() -> List[Meeting]:
            with managed_session(self.engine) as db:
                stmt = (
                    select(Meeting)
                    .where(Meeting.user_id == user_id)
                    .order_by(Meeting.created_at.desc())
                )
                return list(db.exec(stmt).all())

        return await asyncio.to_thread(_sync)

    async def update_status(
        self,
        meeting_id: str,
        status: str,
        error_message: Optional[str] = None,
        provider: Optional[str] = None,
        duration_sec: Optional[int] = None,
    ) -> None:
        def _sync() -> None:
            with managed_session(self.engine) as db:
                meeting = db.get(Meeting, meeting_id)
                if meeting is None:
                    return
                meeting.status = status
                if error_message is not None:
                    meeting.error_message = error_message
                if provider is not None:
                    meeting.transcription_provider = provider
                if duration_sec is not None:
                    meeting.audio_duration_sec = duration_sec
                meeting.updated_at = datetime.now(UTC)
                db.add(meeting)
                db.commit()

        await asyncio.to_thread(_sync)

    async def save_segments(self, meeting_id: str, segments: List[Dict]) -> None:
        def _sync() -> None:
            with managed_session(self.engine) as db:
                # Replace any existing segments (idempotent re-processing).
                existing = db.exec(
                    select(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id)
                ).all()
                for row in existing:
                    db.delete(row)
                for s in segments:
                    db.add(
                        MeetingSegment(
                            meeting_id=meeting_id,
                            seq=s["seq"],
                            speaker_label=s.get("speaker_label", "Speaker 1"),
                            start_ms=s.get("start_ms", 0),
                            end_ms=s.get("end_ms", 0),
                            text=s.get("text", ""),
                        )
                    )
                db.commit()

        await asyncio.to_thread(_sync)

    async def get_segments(self, meeting_id: str) -> List[MeetingSegment]:
        def _sync() -> List[MeetingSegment]:
            with managed_session(self.engine) as db:
                stmt = (
                    select(MeetingSegment)
                    .where(MeetingSegment.meeting_id == meeting_id)
                    .order_by(MeetingSegment.seq)
                )
                return list(db.exec(stmt).all())

        return await asyncio.to_thread(_sync)

    async def save_minutes(self, meeting_id: str, summary: str, content: Dict, model_used: str) -> MeetingMinutes:
        def _sync() -> MeetingMinutes:
            with managed_session(self.engine) as db:
                prev = db.exec(
                    select(MeetingMinutes)
                    .where(MeetingMinutes.meeting_id == meeting_id)
                    .order_by(MeetingMinutes.version.desc())
                ).first()
                version = (prev.version + 1) if prev else 1
                row = MeetingMinutes(
                    meeting_id=meeting_id,
                    summary=summary,
                    content_json=json.dumps(content, ensure_ascii=False),
                    model_used=model_used,
                    version=version,
                )
                db.add(row)
                db.commit()
                db.refresh(row)
                return row

        return await asyncio.to_thread(_sync)

    async def get_latest_minutes(self, meeting_id: str) -> Optional[MeetingMinutes]:
        def _sync() -> Optional[MeetingMinutes]:
            with managed_session(self.engine) as db:
                return db.exec(
                    select(MeetingMinutes)
                    .where(MeetingMinutes.meeting_id == meeting_id)
                    .order_by(MeetingMinutes.version.desc())
                ).first()

        return await asyncio.to_thread(_sync)

    async def update_speaker_names(self, meeting_id: str, mapping: Dict[str, str]) -> None:
        def _sync() -> None:
            with managed_session(self.engine) as db:
                rows = db.exec(
                    select(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id)
                ).all()
                for row in rows:
                    if row.speaker_label in mapping:
                        row.speaker_name = mapping[row.speaker_label]
                        db.add(row)
                db.commit()

        await asyncio.to_thread(_sync)

    async def delete_meeting(self, meeting: Meeting) -> None:
        meeting_id = meeting.id
        object_key = meeting.audio_object_key
        artifact_id = meeting.artifact_id

        def _sync() -> None:
            with managed_session(self.engine) as db:
                for row in db.exec(
                    select(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id)
                ).all():
                    db.delete(row)
                for row in db.exec(
                    select(MeetingMinutes).where(MeetingMinutes.meeting_id == meeting_id)
                ).all():
                    db.delete(row)
                m = db.get(Meeting, meeting_id)
                if m is not None:
                    db.delete(m)
                db.commit()

        await asyncio.to_thread(_sync)
        # Clean up the published artifact + its backing session (if any).
        if artifact_id:
            await database_service.delete_artifact(artifact_id)
            await database_service.delete_session(f"meeting:{meeting_id}")
        await asyncio.to_thread(storage_service.delete_sync, object_key)

    async def fail_stuck_meetings(self) -> int:
        """Mark meetings left in a non-terminal state as FAILED.

        ``process_meeting`` runs as an in-process BackgroundTask, so a restart
        mid-processing orphans any meeting still in UPLOADED/TRANSCRIBING/
        TRANSCRIBED/SUMMARIZING. Called once at startup so they don't poll forever.
        """

        def _sync() -> int:
            with managed_session(self.engine) as db:
                rows = db.exec(
                    select(Meeting).where(~Meeting.status.in_(list(MeetingStatus.TERMINAL)))
                ).all()
                for m in rows:
                    m.status = MeetingStatus.FAILED
                    m.error_message = "서버 재시작으로 처리가 중단되었습니다. 다시 시도해 주세요."
                    m.updated_at = datetime.now(UTC)
                    db.add(m)
                db.commit()
                return len(rows)

        return await asyncio.to_thread(_sync)

    async def set_artifact(self, meeting_id: str, artifact_id: str, public_token: str) -> None:
        def _sync() -> None:
            with managed_session(self.engine) as db:
                meeting = db.get(Meeting, meeting_id)
                if meeting is None:
                    return
                meeting.artifact_id = artifact_id
                meeting.public_token = public_token
                meeting.updated_at = datetime.now(UTC)
                db.add(meeting)
                db.commit()

        await asyncio.to_thread(_sync)

    # ── Orchestration ───────────────────────────────────────────────────────

    @staticmethod
    def _segment_dicts(segments: List[MeetingSegment]) -> List[Dict]:
        return [
            {
                "seq": s.seq,
                "speaker_label": s.speaker_label,
                "speaker_name": s.speaker_name,
                "start_ms": s.start_ms,
                "end_ms": s.end_ms,
                "text": s.text,
            }
            for s in segments
        ]

    async def process_meeting(self, meeting_id: str) -> None:
        """Background pipeline: transcribe → summarize → complete.

        Runs as a FastAPI BackgroundTask. Any failure sets status=FAILED with a
        message; the frontend surfaces it via polling.
        """
        logger.info("meeting_processing_start", meeting_id=meeting_id)
        try:
            meeting = await self.get_meeting(meeting_id)
            if meeting is None:
                logger.error("meeting_processing_not_found", meeting_id=meeting_id)
                return

            # 1. Transcribe (+ diarization). Transcription reads a local file path;
            # with the S3 backend, materialize a temp file and clean it up after.
            await self.update_status(meeting_id, MeetingStatus.TRANSCRIBING)
            if storage_service.use_s3:
                audio_path = await asyncio.to_thread(
                    storage_service.download_to_temp, meeting.audio_object_key
                )
            else:
                audio_path = storage_service.path_for(meeting.audio_object_key)
            try:
                result = await transcription_service.transcribe(
                    audio_path=audio_path,
                    filename=meeting.audio_filename,
                    language=meeting.language,
                    max_speakers=settings.MEETING_MAX_SPEAKERS,
                )
            finally:
                if storage_service.use_s3:
                    await asyncio.to_thread(os.remove, audio_path)
            segments = result["segments"]
            if not segments:
                # Audio is safely stored; transcription just produced nothing
                # (STT unavailable/unauthorized, or no detected speech). Surface
                # this as SAVED rather than a hard failure so the save succeeds.
                await self.update_status(
                    meeting_id,
                    MeetingStatus.SAVED,
                    provider=result.get("provider"),
                    duration_sec=result.get("duration_sec"),
                )
                logger.info("meeting_saved_without_transcript", meeting_id=meeting_id, provider=result.get("provider"))
                return

            await self.save_segments(meeting_id, segments)
            await self.update_status(
                meeting_id,
                MeetingStatus.TRANSCRIBED,
                provider=result.get("provider"),
                duration_sec=result.get("duration_sec"),
            )

            # 2. Summarize → minutes
            await self.update_status(meeting_id, MeetingStatus.SUMMARIZING)
            generated = await minutes_service.generate(meeting.title, segments)
            await self.save_minutes(
                meeting_id,
                summary=generated["summary"],
                content=generated["content"],
                model_used=generated["model_used"],
            )

            await self.update_status(meeting_id, MeetingStatus.COMPLETED)
            logger.info("meeting_processing_complete", meeting_id=meeting_id)
        except Exception as e:
            logger.error("meeting_processing_failed", meeting_id=meeting_id, error=str(e), exc_info=True)
            await self.update_status(
                meeting_id, MeetingStatus.FAILED, error_message=f"처리 중 오류: {str(e)}"
            )

    async def regenerate_minutes(self, meeting_id: str) -> Optional[MeetingMinutes]:
        """Re-run summarization over existing segments (e.g. after speaker mapping)."""
        meeting = await self.get_meeting(meeting_id)
        if meeting is None:
            return None
        segments = await self.get_segments(meeting_id)
        if not segments:
            return None
        generated = await minutes_service.generate(meeting.title, self._segment_dicts(segments))
        return await self.save_minutes(
            meeting_id,
            summary=generated["summary"],
            content=generated["content"],
            model_used=generated["model_used"],
        )

    async def publish_to_artifact(self, meeting: Meeting) -> Optional[Dict]:
        """Render the current minutes to an artifact and publish it.

        Reuses ``database_service.upsert_artifact_version`` + ``publish_artifact``
        so the existing public-link / version-history infrastructure applies.
        """
        latest = await self.get_latest_minutes(meeting.id)
        if latest is None:
            return None
        try:
            content = json.loads(latest.content_json)
        except (ValueError, TypeError):
            content = {"summary": latest.summary}

        markdown = minutes_service.to_markdown(meeting.title, content)
        # artifact.session_id has a FK to the session table — ensure a backing
        # session row exists for this meeting before creating the artifact.
        session_id = f"meeting:{meeting.id}"
        if await database_service.get_session(session_id) is None:
            await database_service.create_session(
                session_id=session_id,
                user_id=meeting.user_id,
                name=meeting.title or "회의록",
            )
        result = await database_service.upsert_artifact_version(
            session_id=session_id,
            user_id=meeting.user_id,
            identifier=f"minutes-{meeting.id}",
            artifact_type="markdown",
            title=meeting.title or "회의록",
            content=markdown,
        )
        artifact_id = result["artifact_id"]
        token = await database_service.publish_artifact(artifact_id)
        await self.set_artifact(meeting.id, artifact_id, token)
        return {"artifact_id": artifact_id, "public_token": token}


meeting_service = MeetingService()
