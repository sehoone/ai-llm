"""skill 도메인 서비스 (ADR-0024). 재사용 지침 프리셋 CRUD.

도메인 책임(ADR-0005): HTTP 경계·인가·영속. 스킬 `body`의 system prompt 합성은 chat이 수행.
"""

from __future__ import annotations

import io
import zipfile

from fastapi import HTTPException
from sqlmodel import Session

from src.domains.skill.model import Skill
from src.domains.skill.repository import SkillRepository
from src.domains.skill.schema import SkillCreateRequest, SkillUpdateRequest
from src.domains.user.model import User, UserRole

# 임포트 파일 크기 상한 — 지침 프리셋은 텍스트라 넉넉히 1MB면 충분(남용·OOM 방지).
_MAX_IMPORT_BYTES = 1_000_000
_IMPORT_EXTS = (".skill.md", ".md", ".txt", ".zip")


def _parse_skill_markdown(text: str, filename: str) -> tuple[str, str | None, str, str, str]:
    """SKILL.md 파싱 (ADR-0024, claude.ai 참고) → (name, description, body, icon, color).

    맨 앞 `---` … `---` 블록을 YAML frontmatter로 해석(간단한 `key: value`만 — pyyaml 미의존).
    frontmatter가 없으면 파일명(확장자 제거)을 이름으로, 전체를 본문으로 쓴다.
    """
    stem = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    for ext in _IMPORT_EXTS:
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    name = stem.strip() or "가져온 스킬"
    description: str | None = None
    icon, color = "sparkles", "#6366f1"
    body = text.strip()

    stripped = text.lstrip()
    if stripped.startswith("---"):
        rest = stripped[3:]
        end = rest.find("\n---")
        if end != -1:
            block, body = rest[:end], rest[end + 4 :].strip()
            for line in block.splitlines():
                key, sep, value = line.partition(":")
                if not sep:
                    continue
                key = key.strip().lower()
                value = value.strip().strip('"').strip("'")
                if not value:
                    continue
                if key == "name":
                    name = value
                elif key == "description":
                    description = value
                elif key == "icon":
                    icon = value
                elif key == "color":
                    color = value
    return name, description, body, icon, color


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

    def import_file(self, user: User, filename: str, raw: bytes) -> Skill:
        """업로드 파일에서 스킬 1건 생성 (ADR-0024 — claude.ai식 SKILL.md 임포트, 경량).

        .md/.txt는 텍스트, .zip은 내부 SKILL.md를 추출해 frontmatter+본문을 파싱한다.
        코드 실행/리소스는 범위 밖(ADR-0024) — 순수 지침 본문만 저장한다.
        """
        if len(raw) > _MAX_IMPORT_BYTES:
            raise HTTPException(status_code=400, detail="파일이 너무 큽니다(최대 1MB).")
        text = self._extract_text(filename, raw)
        name, description, body, icon, color = _parse_skill_markdown(text, filename)
        if not body.strip():
            raise HTTPException(status_code=400, detail="스킬 본문이 비어 있습니다.")
        req = SkillCreateRequest(
            name=name[:100],
            description=description[:500] if description else None,
            body=body,
            icon=icon,
            color=color,
        )
        return self.create(user, req)

    @staticmethod
    def _extract_text(filename: str, raw: bytes) -> str:
        """업로드 바이트에서 스킬 텍스트 추출. zip이면 내부 SKILL.md를 찾아 디코드."""
        is_zip = filename.lower().endswith(".zip") or raw[:2] == b"PK"
        if is_zip:
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    member = next(
                        (n for n in zf.namelist() if n.rsplit("/", 1)[-1].lower() == "skill.md"),
                        None,
                    )
                    if member is None:
                        raise HTTPException(status_code=400, detail="zip 안에 SKILL.md가 없습니다.")
                    return zf.read(member).decode("utf-8", errors="replace")
            except zipfile.BadZipFile as e:
                raise HTTPException(status_code=400, detail="올바른 zip 파일이 아닙니다.") from e
        return raw.decode("utf-8", errors="replace")

    def bodies_for(self, skill_ids: list[str], user: User) -> list[str]:
        """활성 스킬 id → 지침 본문 목록(소유자 스코핑). chat system prompt 합성용."""
        rows = {s.id: s for s in self.repo.list_by_ids(skill_ids, user.id)}
        # 요청 순서 유지(우선순위 — ADR-0024 §2).
        return [rows[sid].body for sid in skill_ids if sid in rows and rows[sid].body.strip()]
