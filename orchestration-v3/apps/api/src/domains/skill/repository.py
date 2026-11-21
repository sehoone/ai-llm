"""skill 도메인 영속 계층 (ADR-0024). skill CRUD (llmonl)."""

from __future__ import annotations

from sqlmodel import Session, select

from src.domains.skill.model import Skill


class SkillRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, s: Skill) -> Skill:
        self.session.add(s)
        self.session.commit()
        self.session.refresh(s)
        return s

    def get(self, skill_id: str) -> Skill | None:
        return self.session.get(Skill, skill_id)

    def list_by_user(self, user_id: int) -> list[Skill]:
        return list(
            self.session.exec(
                select(Skill).where(Skill.user_id == user_id).order_by(Skill.created_at.desc())
            ).all()
        )

    def list_by_ids(self, skill_ids: list[str], user_id: int) -> list[Skill]:
        """소유자 스코핑된 id 조회 — chat 합성 시 활성 스킬 로드용."""
        if not skill_ids:
            return []
        return list(
            self.session.exec(
                select(Skill).where(Skill.id.in_(skill_ids), Skill.user_id == user_id)
            ).all()
        )

    def save(self, s: Skill) -> Skill:
        self.session.add(s)
        self.session.commit()
        self.session.refresh(s)
        return s

    def delete(self, s: Skill) -> None:
        self.session.delete(s)
        self.session.commit()
