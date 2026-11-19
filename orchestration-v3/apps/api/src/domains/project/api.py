"""project 도메인 라우터 (ADR-0021) — 프로젝트 CRUD·소속 대화·지식.

대화는 chat 스택, 지식은 rag를 재사용한다(service 위임). 비스트림 응답은 `ApiResponse[T]`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.artifact.repository import ArtifactRepository
from src.domains.auth.dependencies import get_current_user
from src.domains.project.schema import (
    KnowledgeUploadRequest,
    ProjectCreateRequest,
    ProjectKnowledgeItem,
    ProjectResponse,
    ProjectSessionResponse,
    ProjectUpdateRequest,
)
from src.domains.project.service import ProjectService
from src.domains.chat.schema import SessionCreateRequest
from src.domains.user.model import User

router = APIRouter()


# ── CRUD ──
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[ProjectResponse])
def create_project(
    req: ProjectCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ProjectResponse]:
    p = ProjectService(session).create(user, req)
    return ApiResponse.ok(ProjectResponse.from_model(p))


@router.get("/", response_model=ApiResponse[list[ProjectResponse]])
def list_projects(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[ProjectResponse]]:
    rows = ProjectService(session).list_projects(user)
    return ApiResponse.ok([ProjectResponse.from_model(p) for p in rows])


@router.get("/{project_id}", response_model=ApiResponse[ProjectResponse])
def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ProjectResponse]:
    p = ProjectService(session).get_owned(project_id, user)
    return ApiResponse.ok(ProjectResponse.from_model(p))


@router.put("/{project_id}", response_model=ApiResponse[ProjectResponse])
def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ProjectResponse]:
    p = ProjectService(session).update(project_id, user, req)
    return ApiResponse.ok(ProjectResponse.from_model(p))


@router.delete("/{project_id}", response_model=ApiResponse[None])
def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    ProjectService(session).delete(project_id, user)
    return ApiResponse.ok(None)


# ── 소속 대화 ──
@router.get("/{project_id}/sessions", response_model=ApiResponse[list[ProjectSessionResponse]])
def list_project_sessions(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[ProjectSessionResponse]]:
    rows = ProjectService(session).list_sessions(project_id, user)
    return ApiResponse.ok([ProjectSessionResponse(id=s.id, title=s.title) for s in rows])


@router.post(
    "/{project_id}/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ProjectSessionResponse],
)
def create_project_session(
    project_id: str,
    req: SessionCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ProjectSessionResponse]:
    s = ProjectService(session).create_session(project_id, user, req.title)
    return ApiResponse.ok(ProjectSessionResponse(id=s.id, title=s.title))


# ── 지식 (rag 재사용) ──
@router.get("/{project_id}/knowledge", response_model=ApiResponse[list[ProjectKnowledgeItem]])
def list_knowledge(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[ProjectKnowledgeItem]]:
    docs = ProjectService(session).list_knowledge(project_id, user)
    return ApiResponse.ok([ProjectKnowledgeItem(id=d.id, filename=d.filename) for d in docs])


@router.post(
    "/{project_id}/knowledge",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ProjectKnowledgeItem],
)
def add_knowledge(
    project_id: str,
    req: KnowledgeUploadRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ProjectKnowledgeItem]:
    doc = ProjectService(session).add_knowledge(project_id, user, req.filename, req.content)
    return ApiResponse.ok(ProjectKnowledgeItem(id=doc.id, filename=doc.filename))


@router.delete("/{project_id}/knowledge/{doc_id}", response_model=ApiResponse[None])
def delete_knowledge(
    project_id: str,
    doc_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    ProjectService(session).delete_knowledge(project_id, user, doc_id)
    return ApiResponse.ok(None)


# ── 산출물 집계 (조회 전용) ──
@router.get("/{project_id}/artifacts", response_model=ApiResponse[list[dict]])
def list_project_artifacts(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[dict]]:
    svc = ProjectService(session)
    art_repo = ArtifactRepository(session)
    out: list[dict] = []
    for s in svc.list_sessions(project_id, user):
        for a in art_repo.list_session_artifacts(s.id):
            out.append(
                {
                    "id": a.id,
                    "identifier": a.identifier,
                    "title": a.title,
                    "artifact_type": a.artifact_type,
                    "current_version": a.current_version,
                    "session_id": a.session_id,
                }
            )
    return ApiResponse.ok(out)
