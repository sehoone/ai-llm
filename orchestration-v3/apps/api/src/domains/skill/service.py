"""skill 도메인 서비스 (ADR-0024). 재사용 지침 프리셋 CRUD.

도메인 책임(ADR-0005): HTTP 경계·인가·영속. 스킬 `body`의 system prompt 합성은 chat이 수행.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session

from src.domains.skill.model import Skill
from src.domains.skill.repository import SkillRepository
from src.domains.skill.schema import SkillCreateRequest, SkillUpdateRequest
from src.domains.user.model import User, UserRole


class SkillService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = SkillRepository(session)

    def create(self, user: User, req: SkillCreateRequest) -> Skill:
        s = Skill(
            user_id=user.id,
            name=req.name,
            description=req.description,
            body=req.body,
            icon=req.icon or "sparkles",
            color=req.color or "#6366f1",
        )
        return self.repo.create(s)

    def list_skills(self, user: User) -> list[Skill]:
        return self.repo.list_by_user(user.id)

    def get_owned(self, skill_id: str, user: User) -> Skill:
        s = self.repo.get(skill_id)
        if s is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        if s.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(status_code=403, detail="Not your skill")
        return s

    def update(self, skill_id: str, user: User, req: SkillUpdateRequest) -> Skill:
        s = self.get_owned(skill_id, user)
        for key, value in req.model_dump(exclude_unset=True).items():
            setattr(s, key, value)
        return self.repo.save(s)

    def delete(self, skill_id: str, user: User) -> None:
        s = self.get_owned(skill_id, user)
        self.repo.delete(s)

    def bodies_for(self, skill_ids: list[str], user: User) -> list[str]:
        """활성 스킬 id → 지침 본문 목록(소유자 스코핑). chat system prompt 합성용."""
        rows = {s.id: s for s in self.repo.list_by_ids(skill_ids, user.id)}
        # 요청 순서 유지(우선순위 — ADR-0024 §2).
        return [rows[sid].body for sid in skill_ids if sid in rows and rows[sid].body.strip()]
