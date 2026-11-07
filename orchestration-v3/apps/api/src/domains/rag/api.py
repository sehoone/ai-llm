"""rag 도메인 라우터 (ADR-0012). 그룹·키 CRUD + 문서 수집·검색.

web `src/api/rag-groups.ts` 계약과 경로·필드 정렬(그룹/키 update는 PUT).
chat 사전 주입(`rag_group`)은 Phase 2b에서 연결.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.auth.dependencies import get_current_user
from src.domains.rag.schema import (
    DocumentResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
    GroupCreateRequest,
    GroupResponse,
    GroupUpdateRequest,
    KeyCreateRequest,
    KeyResponse,
    KeyUpdateRequest,
    SearchRequest,
    SearchResultItem,
)
from src.domains.rag.service import RagService
from src.domains.user.model import User

router = APIRouter()


# ── 그룹 ──
@router.get("/groups", response_model=ApiResponse[list[GroupResponse]])
def list_groups(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[list[GroupResponse]]:
    rows = RagService(session).list_groups(user)
    return ApiResponse.ok(
        [GroupResponse.from_model(g, key_count=kc, doc_count=dc) for (g, kc, dc) in rows]
    )


@router.post("/groups", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[GroupResponse])
def create_group(
    req: GroupCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[GroupResponse]:
    svc = RagService(session)
    g = svc.create_group(user, req)
    kc, dc = svc.group_counts(user, g)
    return ApiResponse.ok(GroupResponse.from_model(g, key_count=kc, doc_count=dc))


@router.put("/groups/{group_id}", response_model=ApiResponse[GroupResponse])
def update_group(
    group_id: str,
    req: GroupUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[GroupResponse]:
    svc = RagService(session)
    g = svc.update_group(user, group_id, req)
    kc, dc = svc.group_counts(user, g)
    return ApiResponse.ok(GroupResponse.from_model(g, key_count=kc, doc_count=dc))


@router.delete("/groups/{group_id}", response_model=ApiResponse[None])
def delete_group(
    group_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[None]:
    RagService(session).delete_group(user, group_id)
    return ApiResponse.ok(None)


@router.get("/groups/{group_id}/keys", response_model=ApiResponse[list[KeyResponse]])
def list_group_keys(
    group_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[list[KeyResponse]]:
    rows = RagService(session).list_group_keys(user, group_id)
    return ApiResponse.ok([KeyResponse.from_model(k, doc_count=dc) for (k, dc) in rows])


# ── 키 ──
@router.get("/keys", response_model=ApiResponse[list[KeyResponse]])
def list_keys(
    rag_group: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[KeyResponse]]:
    rows = RagService(session).list_keys(user, rag_group)
    return ApiResponse.ok([KeyResponse.from_model(k, doc_count=dc) for (k, dc) in rows])


@router.post("/keys", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[KeyResponse])
def create_key(
    req: KeyCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[KeyResponse]:
    svc = RagService(session)
    k = svc.create_key(user, req)
    return ApiResponse.ok(KeyResponse.from_model(k, doc_count=svc.key_doc_count(k)))


@router.put("/keys/{key_id}", response_model=ApiResponse[KeyResponse])
def update_key(
    key_id: str,
    req: KeyUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[KeyResponse]:
    svc = RagService(session)
    k = svc.update_key(user, key_id, req)
    return ApiResponse.ok(KeyResponse.from_model(k, doc_count=svc.key_doc_count(k)))


@router.delete("/keys/{key_id}", response_model=ApiResponse[None])
def delete_key(
    key_id: str,
    delete_docs: bool = Query(default=False),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    RagService(session).delete_key(user, key_id, delete_docs)
    return ApiResponse.ok(None)


# ── 문서 ──
@router.post("/documents", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[DocumentUploadResponse])
def upload_document(
    req: DocumentUploadRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[DocumentUploadResponse]:
    doc, indexed = RagService(session).ingest_document(user, req)
    return ApiResponse.ok(
        DocumentUploadResponse(document=DocumentResponse.from_model(doc), chunks_indexed=indexed)
    )


@router.get("/documents", response_model=ApiResponse[list[DocumentResponse]])
def list_documents(
    rag_group: str | None = Query(default=None),
    rag_key: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[DocumentResponse]]:
    docs = RagService(session).list_documents(user, rag_group, rag_key)
    return ApiResponse.ok([DocumentResponse.from_model(d) for d in docs])


@router.delete("/documents/{doc_id}", response_model=ApiResponse[None])
def delete_document(
    doc_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[None]:
    RagService(session).delete_document(user, doc_id)
    return ApiResponse.ok(None)


# ── 검색 (검증용; chat 사전 주입은 Phase 2b) ──
@router.post("/search", response_model=ApiResponse[list[SearchResultItem]])
def search(
    req: SearchRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[SearchResultItem]]:
    results = RagService(session).search(user, req)
    return ApiResponse.ok([SearchResultItem(**r) for r in results])
