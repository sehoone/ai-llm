"""project 도메인 영속 계층 (ADR-0021). project CRUD + 소속 chat_session 조회."""

from __future__ import annotations

from sqlmodel import Session, select

from src.domains.chat.model import ChatSession
from src.domains.project.model import Project


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── project ──
    def create(self, p: Project) -> Project:
        self.session.add(p)
        self.session.commit()
        self.session.refresh(p)
        return p

    def get(self, project_id: str) -> Project | None:
        return self.session.get(Project, project_id)

    def list_by_user(self, user_id: int) -> list[Project]:
        return list(
            self.session.exec(
                select(Project)
                .where(Project.user_id == user_id)
                .order_by(Project.created_at.desc())
            ).all()
        )

    def save(self, p: Project) -> Project:
        self.session.add(p)
        self.session.commit()
        self.session.refresh(p)
        return p

    def delete(self, p: Project) -> None:
        self.session.delete(p)
        self.session.commit()

    # ── 소속 대화(chat_session) ──
    def list_sessions(self, project_id: str) -> list[ChatSession]:
        return list(
            self.session.exec(
                select(ChatSession)
                .where(ChatSession.project_id == project_id)
                .order_by(ChatSession.created_at.desc())
            ).all()
        )
