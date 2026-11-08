"""chat 도메인 영속 계층 (ADR-0008)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.engine import Row
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from src.domains.chat.model import (
    ApprovalStatus,
    ChatApproval,
    ChatAttachment,
    ChatMessage,
    ChatSession,
)
from src.domains.user.model import User


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

    # ── 대화 이력(관리자 뷰) ──
    # 한 줄 = user 메시지(질문) + 같은 세션에서 그 뒤의 첫 assistant 메시지(답변).
    # 답변은 상관 서브쿼리로 뽑아 검색·표시에 함께 쓴다(별도 왕복 없음).
    def _answer_subquery(self):
        """각 user 메시지에 대한 답변(뒤이은 첫 assistant 메시지 content) — 상관 스칼라 서브쿼리."""
        a = aliased(ChatMessage)
        return (
            select(a.content)
            .where(
                a.session_id == ChatMessage.session_id,
                a.role == "assistant",
                a.id > ChatMessage.id,
            )
            .order_by(a.id.asc())
            .limit(1)
            .correlate(ChatMessage)
            .scalar_subquery()
        )

    @staticmethod
    def _search_filter(search: str, answer_subq):
        like = f"%{search}%"
        return or_(
            ChatMessage.content.ilike(like),
            ChatSession.title.ilike(like),
            User.email.ilike(like),
            answer_subq.ilike(like),
        )

    def list_history(self, limit: int, offset: int, search: str = "") -> list[Row]:
        answer_subq = self._answer_subquery()
        stmt = (
            select(
                ChatMessage.id.label("id"),
                ChatMessage.session_id.label("session_id"),
                ChatMessage.content.label("question"),
                ChatMessage.created_at.label("created_at"),
                ChatSession.title.label("session_name"),
                User.email.label("user_email"),
                answer_subq.label("answer"),
            )
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .join(User, User.id == ChatSession.user_id)
            .where(ChatMessage.role == "user")
        )
        if search:
            stmt = stmt.where(self._search_filter(search, answer_subq))
        stmt = (
            stmt.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

    def count_history(self, search: str = "") -> int:
        answer_subq = self._answer_subquery()
        stmt = (
            select(func.count())
            .select_from(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .join(User, User.id == ChatSession.user_id)
            .where(ChatMessage.role == "user")
        )
        if search:
            stmt = stmt.where(self._search_filter(search, answer_subq))
        return self.session.scalar(stmt) or 0

    def get_history_row(self, message_id: int) -> Row | None:
        answer_subq = self._answer_subquery()
        stmt = (
            select(
                ChatMessage.id.label("id"),
                ChatMessage.session_id.label("session_id"),
                ChatMessage.content.label("question"),
                ChatMessage.created_at.label("created_at"),
                ChatSession.title.label("session_name"),
                User.email.label("user_email"),
                answer_subq.label("answer"),
            )
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .join(User, User.id == ChatSession.user_id)
            .where(ChatMessage.id == message_id, ChatMessage.role == "user")
        )
        return self.session.exec(stmt).first()

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
