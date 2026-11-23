"""skill 도메인 라우터 (ADR-0024) — 재사용 지침 프리셋 CRUD. 응답은 `ApiResponse[T]`."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.auth.dependencies import get_current_user
from src.domains.skill.schema import SkillCreateRequest, SkillResponse, SkillUpdateRequest
from src.domains.skill.service import SkillService
from src.domains.user.model import User

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[SkillResponse])
def create_skill(
    req: SkillCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[SkillResponse]:
    s = SkillService(session).create(user, req)
    return ApiResponse.ok(SkillResponse.from_model(s))


@router.post("/import", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[SkillResponse])
async def import_skill(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[SkillResponse]:
    """SKILL.md / .md / .txt / .zip 업로드 → 스킬 1건 생성 (ADR-0024, claude.ai 참고·경량)."""
    raw = await file.read()
    s = SkillService(session).import_file(user, file.filename or "skill.md", raw)
    return ApiResponse.ok(SkillResponse.from_model(s))


@router.get("", response_model=ApiResponse[list[SkillResponse]])
def list_skills(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[SkillResponse]]:
    rows = SkillService(session).list_skills(user)
    return ApiResponse.ok([SkillResponse.from_model(s) for s in rows])


@router.get("/{skill_id}", response_model=ApiResponse[SkillResponse])
def get_skill(
    skill_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[SkillResponse]:
    s = SkillService(session).get_owned(skill_id, user)
    return ApiResponse.ok(SkillResponse.from_model(s))


@router.put("/{skill_id}", response_model=ApiResponse[SkillResponse])
def update_skill(
    skill_id: str,
    req: SkillUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[SkillResponse]:
    s = SkillService(session).update(skill_id, user, req)
    return ApiResponse.ok(SkillResponse.from_model(s))


@router.delete("/{skill_id}", response_model=ApiResponse[None])
def delete_skill(
    skill_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    SkillService(session).delete(skill_id, user)
    return ApiResponse.ok(None)
