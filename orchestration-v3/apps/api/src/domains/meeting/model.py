"""meeting 도메인 테이블 — 회의·전사 세그먼트·생성된 회의록. schema: llmonl. FK 없음."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid.uuid4().hex


class MeetingStatus:
    """회의 처리 상태(문자열 상수, `Meeting.status`에 저장)."""

    UPLOADED = "UPLOADED"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSCRIBED = "TRANSCRIBED"
    SUMMARIZING = "SUMMARIZING"
    COMPLETED = "COMPLETED"
    SAVED = "SAVED"  # 오디오는 저장됐으나 전사 결과 없음(STT 미설정 등)
    FAILED = "FAILED"

    TERMINAL = frozenset({COMPLETED, SAVED, FAILED})


class Meeting(SQLModel, table=True):
    """단일 녹음 회의와 그 처리 라이프사이클.

    오디오는 `core/storage`에 저장되고 `audio_object_key`로 참조된다. 처리는 status를
    UPLOADED → TRANSCRIBING → TRANSCRIBED → SUMMARIZING → COMPLETED(또는 FAILED)로 전진.
    발행 시 회의록을 아티팩트로 렌더하고 `artifact_id`를 기록한다.
    """

    __tablename__ = "meeting"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: int = Field(index=True)
    title: str = Field(default="")
    status: str = Field(default=MeetingStatus.UPLOADED, index=True)
    audio_object_key: str
    audio_filename: str = Field(default="")
    audio_duration_sec: int | None = Field(default=None)
    language: str = Field(default="ko-KR")
    transcription_provider: str | None = Field(default=None)  # "azure" | "whisper"
    artifact_id: str | None = Field(default=None, index=True)
    public_token: str | None = Field(default=None, index=True)
    error_message: str | None = Field(default=None)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class MeetingSegment(SQLModel, table=True):
    """화자 분리된 전사 세그먼트 한 개(한 화자의 한 발화)."""

    __tablename__ = "meeting_segment"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    meeting_id: str = Field(index=True)
    seq: int
    speaker_label: str = Field(default="Speaker 1")  # 공급자 할당 라벨
    speaker_name: str | None = Field(default=None)   # 사용자 매핑 실명
    start_ms: int = Field(default=0)
    end_ms: int = Field(default=0)
    text: str = Field(default="")


class MeetingMinutes(SQLModel, table=True):
    """생성된 구조화 회의록(재생성 시 버전 증가)."""

    __tablename__ = "meeting_minutes"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    meeting_id: str = Field(index=True)
    summary: str = Field(default="")
    content_json: str = Field(default="{}")  # 구조화 회의록, JSON 인코딩
    model_used: str = Field(default="")
    version: int = Field(default=1)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
