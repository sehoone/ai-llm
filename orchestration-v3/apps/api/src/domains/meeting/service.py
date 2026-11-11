"""meeting 도메인 서비스 — 라이프사이클 오케스트레이션 + 영속 + 인가.

도메인 책임(ADR-0005): HTTP 경계·관계형 영속·인가·오케스트레이션. AI 연산(전사·회의록 생성)은
`engine/transcription`에 위임한다. LLM 선택은 `llm_resource` 테이블에서 해석해 `LlmConfig`로 주입
(engine은 DB 미조회). 전사 외부 서비스 좌표는 settings에서 해석해 `TranscriptionConfig`로 주입.

발행은 `domains/artifact`를 재사용(공개 링크·버전 관리 인프라 공유).
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import HTTPException
from sqlmodel import Session

from src.core.config import settings
from src.core.db import engine as _db_engine
from src.core.storage import get_storage
from src.domains.artifact.repository import ArtifactRepository
from src.platform.llm_resource.model import LlmResource
from src.platform.llm_resource.repository import LlmResourceRepository
from src.domains.meeting.model import Meeting, MeetingStatus
from src.domains.meeting.repository import MeetingRepository
from src.platform.user.model import User, UserRole
from src.engine.llm.config import LlmConfig
from src.engine.transcription import (
    TranscriptionConfig,
    generate_minutes,
    minutes_to_markdown,
    transcribe,
)

logger = logging.getLogger(__name__)

_AUDIO_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
}

_PUBLISH_SESSION_ID = 0  # meeting 발행 아티팩트는 chat 세션이 없다 — artifact_id/token으로만 주소화


def audio_content_type(object_key: str) -> str:
    """오브젝트 키 확장자로부터 오디오 MIME 타입(없으면 octet-stream)."""
    return _AUDIO_CONTENT_TYPES.get(Path(object_key).suffix.lower(), "application/octet-stream")


def meeting_storage():
    """녹음 전용 버킷(settings.meeting_audio_bucket) 스토리지 — 첨부(chat-attachments)와 분리."""
    return get_storage(settings.meeting_audio_bucket)


def _config_from_resource(r: LlmResource) -> LlmConfig:
    """llm_resource 행 → LlmConfig (azure는 deployment_name을 model로)."""
    model = r.deployment_name if r.provider == "azure" else (r.model_name or r.name)
    return LlmConfig(
        provider=r.provider,
        model=model or r.name,
        api_key=r.api_key or None,
        api_base=r.api_base or None,
        api_version=r.api_version or None,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens or None,
    )


class MeetingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = MeetingRepository(session)

    # ── 설정 해석 ──
    def _chat_config(self) -> LlmConfig | None:
        r = LlmResourceRepository(self.session).default_chat_model()
        return _config_from_resource(r) if r is not None else None

    @staticmethod
    def _transcription_config() -> TranscriptionConfig:
        return TranscriptionConfig(
            azure_key=settings.azure_speech_key,
            azure_region=settings.azure_speech_region,
            openai_key=settings.openai_api_key,
            stt_model=settings.openai_stt_model,
        )

    # ── 인가 ──
    def get_owned(self, meeting_id: str, user: User) -> Meeting:
        """회의 조회 + 소유권 강제(관리자는 전체 접근)."""
        meeting = self.repo.get(meeting_id)
        if meeting is None:
            raise HTTPException(status_code=404, detail="Meeting not found")
        is_admin = user.role in (UserRole.ADMIN, UserRole.SUPERADMIN)
        if not is_admin and meeting.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        return meeting

    # ── CRUD ──
    async def create_meeting(
        self, *, user_id: int, title: str, filename: str, data: bytes, language: str
    ) -> Meeting:
        storage = meeting_storage()
        key, _ = await asyncio.to_thread(storage.save_bytes, data, f"meetings/{user_id}", filename)
        meeting = self.repo.create(
            Meeting(
                user_id=user_id,
                title=title,
                status=MeetingStatus.UPLOADED,
                audio_object_key=key,
                audio_filename=filename,
                language=language,
            )
        )
        return meeting

    def list_meetings(self, user_id: int) -> list[Meeting]:
        return self.repo.list_by_user(user_id)

    def get_segments(self, meeting_id: str):
        return self.repo.get_segments(meeting_id)

    def get_latest_minutes(self, meeting_id: str):
        return self.repo.get_latest_minutes(meeting_id)

    def update_speaker_names(self, meeting_id: str, mapping: dict[str, str]) -> None:
        self.repo.update_speaker_names(meeting_id, mapping)

    def save_minutes_manual(self, meeting_id: str, *, summary: str, content: dict):
        return self.repo.save_minutes(meeting_id, summary=summary, content=content, model_used="manual")

    def delete_meeting(self, meeting: Meeting) -> None:
        artifact_id = meeting.artifact_id
        object_key = meeting.audio_object_key
        self.repo.delete(meeting.id)
        if artifact_id:
            art_repo = ArtifactRepository(self.session)
            art = art_repo.get_artifact(artifact_id)
            if art is not None:
                art_repo.delete_artifact(art)
        try:
            meeting_storage().delete(object_key)
        except Exception:
            logger.warning("meeting_audio_delete_failed key=%s", object_key, exc_info=True)

    # ── 오케스트레이션 ──
    async def process(self, meeting_id: str) -> None:
        """백그라운드 파이프라인: 전사 → 요약 → 완료. 실패 시 status=FAILED."""
        logger.info("meeting_processing_start meeting_id=%s", meeting_id)
        try:
            meeting = self.repo.get(meeting_id)
            if meeting is None:
                logger.error("meeting_processing_not_found meeting_id=%s", meeting_id)
                return

            # 1. 전사(+화자 분리). 오디오 바이트를 스토리지에서 읽어 전사기에 전달.
            self.repo.update_status(meeting_id, MeetingStatus.TRANSCRIBING)
            storage = meeting_storage()
            key = meeting.audio_object_key
            audio_bytes = await asyncio.to_thread(lambda: b"".join(storage.open_stream(key)))
            result = await transcribe(
                audio_bytes,
                meeting.audio_filename,
                meeting.language,
                settings.meeting_max_speakers,
                config=self._transcription_config(),
            )
            segments = result["segments"]
            if not segments:
                # 오디오는 안전히 저장됨; 전사 결과만 없음 → SAVED(하드 실패 아님).
                self.repo.update_status(
                    meeting_id,
                    MeetingStatus.SAVED,
                    provider=result.get("provider"),
                    duration_sec=result.get("duration_sec"),
                )
                logger.info("meeting_saved_without_transcript meeting_id=%s", meeting_id)
                return

            self.repo.replace_segments(meeting_id, segments)
            self.repo.update_status(
                meeting_id,
                MeetingStatus.TRANSCRIBED,
                provider=result.get("provider"),
                duration_sec=result.get("duration_sec"),
            )

            # 2. 요약 → 회의록
            self.repo.update_status(meeting_id, MeetingStatus.SUMMARIZING)
            chat_cfg = self._chat_config()
            if chat_cfg is not None:
                generated = await asyncio.to_thread(
                    generate_minutes,
                    meeting.title,
                    segments,
                    chat_cfg,
                    map_reduce_threshold=settings.meeting_map_reduce_char_threshold,
                    chunk_size=settings.meeting_chunk_char_size,
                )
            else:
                generated = {
                    "summary": "활성 chat LLM 리소스가 없어 회의록을 생성하지 못했습니다.",
                    "content": {"summary": "활성 chat LLM 리소스가 없어 회의록을 생성하지 못했습니다. 전사는 저장되었습니다."},
                    "model_used": "none",
                }
            self.repo.save_minutes(
                meeting_id,
                summary=generated["summary"],
                content=generated["content"],
                model_used=generated["model_used"],
            )
            self.repo.update_status(meeting_id, MeetingStatus.COMPLETED)
            logger.info("meeting_processing_complete meeting_id=%s", meeting_id)
        except Exception as e:
            logger.exception("meeting_processing_failed meeting_id=%s", meeting_id)
            self.repo.update_status(meeting_id, MeetingStatus.FAILED, error_message=f"처리 중 오류: {e}")

    async def regenerate_minutes(self, meeting_id: str):
        """기존 세그먼트로 요약 재실행(예: 화자 매핑 후). 세그먼트 없거나 LLM 없으면 None."""
        meeting = self.repo.get(meeting_id)
        if meeting is None:
            return None
        seg_models = self.repo.get_segments(meeting_id)
        if not seg_models:
            return None
        chat_cfg = self._chat_config()
        if chat_cfg is None:
            return None
        segments = [
            {
                "seq": s.seq,
                "speaker_label": s.speaker_label,
                "speaker_name": s.speaker_name,
                "start_ms": s.start_ms,
                "end_ms": s.end_ms,
                "text": s.text,
            }
            for s in seg_models
        ]
        generated = await asyncio.to_thread(
            generate_minutes,
            meeting.title,
            segments,
            chat_cfg,
            map_reduce_threshold=settings.meeting_map_reduce_char_threshold,
            chunk_size=settings.meeting_chunk_char_size,
        )
        return self.repo.save_minutes(
            meeting_id,
            summary=generated["summary"],
            content=generated["content"],
            model_used=generated["model_used"],
        )

    def publish_to_artifact(self, meeting: Meeting) -> dict | None:
        """현재 회의록을 마크다운 아티팩트로 렌더·발행. 회의록 없으면 None."""
        latest = self.repo.get_latest_minutes(meeting.id)
        if latest is None:
            return None
        try:
            content = json.loads(latest.content_json)
        except (ValueError, TypeError):
            content = {"summary": latest.summary}

        markdown = minutes_to_markdown(meeting.title, content)
        art_repo = ArtifactRepository(self.session)
        result = art_repo.upsert_version(
            session_id=_PUBLISH_SESSION_ID,
            user_id=meeting.user_id,
            identifier=f"minutes-{meeting.id}",
            artifact_type="text/markdown",
            title=meeting.title or "회의록",
            content=markdown,
        )
        art = art_repo.get_artifact(result["artifact_id"])
        if art is None:
            return None
        token = art_repo.publish(art)
        self.repo.set_artifact(meeting.id, art.id, token)
        return {"artifact_id": art.id, "public_token": token}


async def run_process_meeting(meeting_id: str) -> None:
    """BackgroundTask 진입점 — 요청 세션과 분리된 자체 세션을 연다."""
    with Session(_db_engine) as session:
        await MeetingService(session).process(meeting_id)


def fail_stuck_meetings() -> int:
    """기동 시 비종료 상태로 남은 회의를 FAILED로 표시(인프로세스 BackgroundTask 고아 정리)."""
    with Session(_db_engine) as session:
        return MeetingRepository(session).fail_stuck()
