"""meeting 도메인 요청/응답 스키마. web `src/api/meetings.ts` 계약과 필드 정렬."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from src.domains.meeting.model import Meeting, MeetingSegment


class MeetingSummary(BaseModel):
    """목록용 회의 메타(전사/회의록 본문 제외)."""

    id: str
    title: str
    status: str
    audio_filename: str
    audio_duration_sec: int | None = None
    language: str
    transcription_provider: str | None = None
    artifact_id: str | None = None
    public_token: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, m: Meeting) -> "MeetingSummary":
        return cls(
            id=m.id,
            title=m.title,
            status=m.status,
            audio_filename=m.audio_filename,
            audio_duration_sec=m.audio_duration_sec,
            language=m.language,
            transcription_provider=m.transcription_provider,
            artifact_id=m.artifact_id,
            public_token=m.public_token,
            error_message=m.error_message,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


class MeetingListResponse(BaseModel):
    items: list[MeetingSummary]


class SegmentResponse(BaseModel):
    seq: int
    speaker_label: str
    speaker_name: str | None = None
    start_ms: int
    end_ms: int
    text: str

    @classmethod
    def from_model(cls, s: MeetingSegment) -> "SegmentResponse":
        return cls(
            seq=s.seq,
            speaker_label=s.speaker_label,
            speaker_name=s.speaker_name,
            start_ms=s.start_ms,
            end_ms=s.end_ms,
            text=s.text,
        )


class TranscriptResponse(BaseModel):
    meeting_id: str
    segments: list[SegmentResponse]


class MinutesResponse(BaseModel):
    """생성된 회의록 — `content`는 파싱된 구조화 객체."""

    summary: str
    content: dict
    model_used: str
    version: int


class MeetingDetailResponse(MeetingSummary):
    """회의 메타 + 현재 회의록(생성됐다면)."""

    minutes: MinutesResponse | None = None


class CreateMeetingResponse(BaseModel):
    id: str
    status: str


class SpeakerMappingRequest(BaseModel):
    """공급자 화자 라벨 → 실명 매핑. 예: ``{"Speaker 1": "김팀장"}``."""

    mapping: dict[str, str]


class UpdateMinutesRequest(BaseModel):
    """현재 회의록 덮어쓰기(수동 편집). `content`는 구조화 객체."""

    summary: str | None = None
    content: dict


class PublishResponse(BaseModel):
    public_token: str
    artifact_id: str
