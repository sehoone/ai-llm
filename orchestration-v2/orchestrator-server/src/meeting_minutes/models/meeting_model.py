"""Meeting-minutes models — a meeting, its transcript segments, and generated minutes."""

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class MeetingStatus:
    """Processing states for a meeting (string constants, stored on ``Meeting.status``)."""

    UPLOADED = "UPLOADED"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSCRIBED = "TRANSCRIBED"
    SUMMARIZING = "SUMMARIZING"
    COMPLETED = "COMPLETED"
    SAVED = "SAVED"  # audio stored, but transcription produced no result (e.g. STT unavailable)
    FAILED = "FAILED"

    TERMINAL = frozenset({COMPLETED, SAVED, FAILED})


class Meeting(SQLModel, table=True):
    """A single recorded meeting and its processing lifecycle.

    Audio is stored by :class:`StorageService` and referenced by
    ``audio_object_key``. Processing advances ``status`` through
    UPLOADED → TRANSCRIBING → TRANSCRIBED → SUMMARIZING → COMPLETED (or FAILED).
    Publishing renders the minutes into an artifact and records ``artifact_id``.
    """

    __tablename__ = "meeting"

    id: str = Field(primary_key=True)  # uuid
    user_id: int = Field(index=True)
    title: str = Field(default="")
    status: str = Field(default=MeetingStatus.UPLOADED, index=True)
    audio_object_key: str = Field(nullable=False)
    audio_filename: str = Field(default="")
    audio_duration_sec: Optional[int] = Field(default=None)
    language: str = Field(default="ko-KR")
    transcription_provider: Optional[str] = Field(default=None)  # "azure" | "whisper"
    artifact_id: Optional[str] = Field(default=None, index=True)
    public_token: Optional[str] = Field(default=None, index=True)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MeetingSegment(SQLModel, table=True):
    """A single diarized transcript segment (one utterance by one speaker)."""

    __tablename__ = "meeting_segment"

    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: str = Field(index=True)
    seq: int = Field(nullable=False)
    speaker_label: str = Field(default="Speaker 1")  # provider-assigned label
    speaker_name: Optional[str] = Field(default=None)  # user-mapped real name
    start_ms: int = Field(default=0)
    end_ms: int = Field(default=0)
    text: str = Field(default="")


class MeetingMinutes(SQLModel, table=True):
    """Generated, structured minutes for a meeting (versioned on regeneration)."""

    __tablename__ = "meeting_minutes"

    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: str = Field(index=True)
    summary: str = Field(default="")
    content_json: str = Field(default="{}")  # structured minutes, JSON-encoded
    model_used: str = Field(default="")
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
