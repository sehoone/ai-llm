"""gpts 도메인 영속 계층. custom_gpt·gpt_session·gpt_chat_message CRUD (llmonl)."""

from __future__ import annotations

from sqlmodel import Session, select

from src.domains.gpts.model import CustomGpt, GptChatMessage, GptSession


class GptsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── CustomGPT ──
    def create_gpt(self, gpt: CustomGpt) -> CustomGpt:
        self.session.add(gpt)
        self.session.commit()
        self.session.refresh(gpt)
        return gpt

    def get_gpt(self, gpt_id: str) -> CustomGpt | None:
        return self.session.get(CustomGpt, gpt_id)

    def list_gpts(self, user_id: int) -> list[CustomGpt]:
        return list(
            self.session.exec(
                select(CustomGpt)
                .where(CustomGpt.user_id == user_id)
                .order_by(CustomGpt.created_at.desc())
            ).all()
        )

    def save_gpt(self, gpt: CustomGpt) -> CustomGpt:
        self.session.add(gpt)
        self.session.commit()
        self.session.refresh(gpt)
        return gpt

    def delete_gpt(self, gpt: CustomGpt) -> None:
        """GPT + 종속 세션·메시지를 함께 제거(FK 없이 명시 정리)."""
        sessions = self.list_sessions(gpt.id)
        for s in sessions:
            self._delete_session_messages(s.id)
            self.session.delete(s)
        self.session.delete(gpt)
        self.session.commit()

    # ── 세션 ──
    def create_session(self, s: GptSession) -> GptSession:
        self.session.add(s)
        self.session.commit()
        self.session.refresh(s)
        return s

    def get_session(self, session_id: str) -> GptSession | None:
        return self.session.get(GptSession, session_id)

    def list_sessions(self, custom_gpt_id: str, user_id: int | None = None) -> list[GptSession]:
        stmt = select(GptSession).where(GptSession.custom_gpt_id == custom_gpt_id)
        if user_id is not None:
            stmt = stmt.where(GptSession.user_id == user_id)
        return list(self.session.exec(stmt.order_by(GptSession.created_at.desc())).all())

    def rename_session(self, s: GptSession, name: str) -> GptSession:
        s.name = name
        self.session.add(s)
        self.session.commit()
        self.session.refresh(s)
        return s

    def delete_session(self, s: GptSession) -> None:
        self._delete_session_messages(s.id)
        self.session.delete(s)
        self.session.commit()

    # ── 메시지 ──
    def add_message(self, session_id: str, question: str, answer: str) -> GptChatMessage:
        m = GptChatMessage(session_id=session_id, question=question, answer=answer)
        self.session.add(m)
        self.session.commit()
        self.session.refresh(m)
        return m

    def list_messages(self, session_id: str) -> list[GptChatMessage]:
        return list(
            self.session.exec(
                select(GptChatMessage)
                .where(GptChatMessage.session_id == session_id)
                .order_by(GptChatMessage.created_at.asc(), GptChatMessage.id.asc())
            ).all()
        )

    def _delete_session_messages(self, session_id: str) -> None:
        for m in self.list_messages(session_id):
            self.session.delete(m)

    def clear_messages(self, session_id: str) -> None:
        self._delete_session_messages(session_id)
        self.session.commit()
