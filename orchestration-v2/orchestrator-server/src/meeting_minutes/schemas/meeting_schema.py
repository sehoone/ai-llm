"""Request/response schemas for the meeting-minutes API."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class MeetingSummary(BaseModel):
    """Meeting metadata for list views (no transcript/minutes body)."""

    id: str
    title: str
    status: str
    audio_filename: str
    audio_duration_sec: Optional[int] = None
    language: str
    transcription_provider: Optional[str] = None
    artifact_id: Optional[str] = None
    public_token: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MeetingListResponse(BaseModel):
    items: List[MeetingSummary]


class SegmentResponse(BaseModel):
    seq: int
    speaker_label: str
    speaker_name: Optional[str] = None
    start_ms: int
    end_ms: int
    text: str


class TranscriptResponse(BaseModel):
    meeting_id: str
    segments: List[SegmentResponse]


class MinutesResponse(BaseModel):
    """Generated minutes — ``content`` is the parsed structured object."""

    summary: str
    content: Dict
    model_used: str
    version: int


class MeetingDetailResponse(MeetingSummary):
    """Meeting metadata plus its current minutes (if generated)."""

    minutes: Optional[MinutesResponse] = None


class CreateMeetingResponse(BaseModel):
    id: str
    status: str


class SpeakerMappingRequest(BaseModel):
    """Map provider speaker labels to real names, e.g. ``{"Speaker 1": "김팀장"}``."""

    mapping: Dict[str, str]


class UpdateMinutesRequest(BaseModel):
    """Overwrite the current minutes (manual edit). ``content`` is the structured object."""

    summary: Optional[str] = None
    content: Dict


class PublishResponse(BaseModel):
    public_token: str
    artifact_id: str
