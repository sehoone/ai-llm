"""meeting 도메인 영속 계층 — 동기 Session. V2 MeetingService DB 접근분을 이식."""

from __future__ import annotations

import json
from datetime import datetime

from sqlmodel import Session, select

from src.domains.meeting.model import Meeting, MeetingMinutes, MeetingSegment, MeetingStatus


class MeetingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── 회의 CRUD ──
    def create(self, meeting: Meeting) -> Meeting:
        self.session.add(meeting)
        self.session.commit()
        self.session.refresh(meeting)
        return meeting

    def get(self, meeting_id: str) -> Meeting | None:
        return self.session.get(Meeting, meeting_id)

    def list_by_user(self, user_id: int) -> list[Meeting]:
        return list(
            self.session.exec(
                select(Meeting).where(Meeting.user_id == user_id).order_by(Meeting.created_at.desc())
            ).all()
        )

    def update_status(
        self,
        meeting_id: str,
        status: str,
        *,
        error_message: str | None = None,
        provider: str | None = None,
        duration_sec: int | None = None,
    ) -> None:
        meeting = self.session.get(Meeting, meeting_id)
        if meeting is None:
            return
        meeting.status = status
        if error_message is not None:
            meeting.error_message = error_message
        if provider is not None:
            meeting.transcription_provider = provider
        if duration_sec is not None:
            meeting.audio_duration_sec = duration_sec
        meeting.updated_at = datetime.utcnow()
        self.session.add(meeting)
        self.session.commit()

    def set_artifact(self, meeting_id: str, artifact_id: str, public_token: str) -> None:
        meeting = self.session.get(Meeting, meeting_id)
        if meeting is None:
            return
        meeting.artifact_id = artifact_id
        meeting.public_token = public_token
        meeting.updated_at = datetime.utcnow()
        self.session.add(meeting)
        self.session.commit()

    def delete(self, meeting_id: str) -> None:
        for row in self.session.exec(
            select(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id)
        ).all():
            self.session.delete(row)
        for row in self.session.exec(
            select(MeetingMinutes).where(MeetingMinutes.meeting_id == meeting_id)
        ).all():
            self.session.delete(row)
        m = self.session.get(Meeting, meeting_id)
        if m is not None:
            self.session.delete(m)
        self.session.commit()

    def fail_stuck(self) -> int:
        """비종료 상태로 남은 회의를 FAILED로 표시(기동 시 고아 정리)."""
        rows = self.session.exec(
            select(Meeting).where(~Meeting.status.in_(list(MeetingStatus.TERMINAL)))
        ).all()
        for m in rows:
            m.status = MeetingStatus.FAILED
            m.error_message = "서버 재시작으로 처리가 중단되었습니다. 다시 시도해 주세요."
            m.updated_at = datetime.utcnow()
            self.session.add(m)
        self.session.commit()
        return len(rows)

    # ── 세그먼트 ──
    def replace_segments(self, meeting_id: str, segments: list[dict]) -> None:
        existing = self.session.exec(
            select(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id)
        ).all()
        for row in existing:
            self.session.delete(row)
        for s in segments:
            self.session.add(
                MeetingSegment(
                    meeting_id=meeting_id,
                    seq=s["seq"],
                    speaker_label=s.get("speaker_label", "Speaker 1"),
                    start_ms=s.get("start_ms", 0),
                    end_ms=s.get("end_ms", 0),
                    text=s.get("text", ""),
                )
            )
        self.session.commit()

    def get_segments(self, meeting_id: str) -> list[MeetingSegment]:
        return list(
            self.session.exec(
                select(MeetingSegment)
                .where(MeetingSegment.meeting_id == meeting_id)
                .order_by(MeetingSegment.seq)
            ).all()
        )

    def update_speaker_names(self, meeting_id: str, mapping: dict[str, str]) -> None:
        rows = self.session.exec(
            select(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id)
        ).all()
        for row in rows:
            if row.speaker_label in mapping:
                row.speaker_name = mapping[row.speaker_label]
                self.session.add(row)
        self.session.commit()

    # ── 회의록 ──
    def save_minutes(self, meeting_id: str, *, summary: str, content: dict, model_used: str) -> MeetingMinutes:
        prev = self.session.exec(
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
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_latest_minutes(self, meeting_id: str) -> MeetingMinutes | None:
        return self.session.exec(
            select(MeetingMinutes)
            .where(MeetingMinutes.meeting_id == meeting_id)
            .order_by(MeetingMinutes.version.desc())
        ).first()
