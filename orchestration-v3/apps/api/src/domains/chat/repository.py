"""chat 도메인 영속 계층 (ADR-0008)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from src.domains.chat.model import (
    ApprovalStatus,
    ChatApproval,
    ChatAttachment,
    ChatMessage,
    ChatSession,
)


class ChatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── 세션 ──
    def create_session(self, user_id: int, title: str) -> ChatSession:
        s = ChatSession(user_id=user_id, title=title)
        self.session.add(s)
        self.session.commit()
        self.session.refresh(s)
        return s

    def get_session(self, session_id: int) -> ChatSession | None:
        return self.session.get(ChatSession, session_id)

    def list_sessions(self, user_id: int) -> list[ChatSession]:
        return list(
            self.session.exec(
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.created_at.desc())
            ).all()
        )

    def rename_session(self, session: ChatSession, title: str) -> ChatSession:
        session.title = title
        session.updated_at = datetime.utcnow()
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    def delete_session(self, session: ChatSession) -> None:
        """세션 + 종속 메시지·승인·첨부 메타를 함께 제거(FK 없이 명시 정리). 파일 삭제는 service."""
        for m in self.list_messages(session.id):
            self.session.delete(m)
        approvals = self.session.exec(
            select(ChatApproval).where(ChatApproval.session_id == session.id)
        ).all()
        for a in approvals:
            self.session.delete(a)
        for att in self.list_session_attachments(session.id):
            self.session.delete(att)
        self.session.delete(session)
        self.session.commit()

    # ── 첨부 (ADR-0014) ──
    def add_attachment(
        self,
        *,
        message_id: int,
        session_id: int,
        filename: str,
        content_type: str,
        file_size: int,
        storage_path: str,
    ) -> ChatAttachment:
        a = ChatAttachment(
            message_id=message_id,
            session_id=session_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            storage_path=storage_path,
        )
        self.session.add(a)
        self.session.commit()
        self.session.refresh(a)
        return a

    def get_attachment(self, attachment_id: int) -> ChatAttachment | None:
        return self.session.get(ChatAttachment, attachment_id)

    def attachments_by_message_ids(self, message_ids: list[int]) -> dict[int, list[ChatAttachment]]:
        if not message_ids:
            return {}
        rows = self.session.exec(
            select(ChatAttachment).where(ChatAttachment.message_id.in_(message_ids))
        ).all()
        out: dict[int, list[ChatAttachment]] = {}
        for a in rows:
            out.setdefault(a.message_id, []).append(a)
        return out

    def list_session_attachments(self, session_id: int) -> list[ChatAttachment]:
        return list(
            self.session.exec(
                select(ChatAttachment).where(ChatAttachment.session_id == session_id)
            ).all()
        )

    # ── 메시지 ──
    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> ChatMessage:
        m = ChatMessage(session_id=session_id, role=role, content=content, tool_calls=tool_calls)
        self.session.add(m)
        self.session.commit()
        self.session.refresh(m)
        return m

    def list_messages(self, session_id: int) -> list[ChatMessage]:
        return list(
            self.session.exec(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            ).all()
        )

    # ── 승인 ──
    def save_approvals(
        self,
        session_id: int,
        user_id: int,
        group_key: str,
        requests: list[dict[str, Any]],
        ttl_seconds: int,
    ) -> list[ChatApproval]:
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        rows = [
            ChatApproval(
                session_id=session_id,
                user_id=user_id,
                group_key=group_key,
                tool_call_id=r["tool_call_id"],
                tool_name=r["name"],
                args=r.get("args", {}),
                tier=r.get("tier", "CONFIRM"),
                allow_edit=r.get("allow_edit", True),
                reason=r.get("reason"),
                expires_at=expires_at,
            )
            for r in requests
        ]
        self.session.add_all(rows)
        self.session.commit()
        for row in rows:
            self.session.refresh(row)
        return rows

    def pending_by_group(self, session_id: int, group_key: str) -> list[ChatApproval]:
        return list(
            self.session.exec(
                select(ChatApproval).where(
                    ChatApproval.session_id == session_id,
                    ChatApproval.group_key == group_key,
                    ChatApproval.status == ApprovalStatus.PENDING,
                )
            ).all()
        )

    def mark(
        self, row: ChatApproval, status: ApprovalStatus, decided_by: int | None
    ) -> ChatApproval:
        row.status = status
        row.decided_by = decided_by
        row.decided_at = datetime.utcnow()
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row
