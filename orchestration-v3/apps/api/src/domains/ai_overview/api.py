"""ai_overview 도메인 라우터. web `src/api/ai-overview.ts` 계약과 경로·필드 정렬.

응답은 `ApiResponse[T]`로 감싼다(axios 자동 unwrap). `/search`만 NDJSON 스트리밍(래퍼 미적용).
FastAPI 매칭 순서상 static 경로(`/documents/upload`·`/batch`·`/all`)를 `/documents/{doc_id}`보다
먼저 등록한다.
"""

from __future__ import annotations

import json

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.ai_overview.schema import (
    BatchDeleteRequest,
    DocumentCreateRequest,
    DocumentDetailResponse,
    DocumentListResponse,
    GenerateKeywordsRequest,
    KeywordResponse,
    SearchRequest,
)
from src.domains.ai_overview.service import AiOverviewService, run_keyword_generation_job
from src.domains.ai_overview.upload_job import create_job, get_job
from src.platform.auth.dependencies import get_current_user
from src.platform.user.model import User

router = APIRouter()

MAX_UPLOAD_ITEMS = 10_000


# ── JSON 업로드 (static — /{doc_id}보다 먼저) ──
@router.post("/documents/upload", response_model=ApiResponse[dict])
async def upload_documents_json(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    system_prompt: str | None = Form(default=None),
    model: str | None = Form(default=None),  # (compat) 무시
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[dict]:
    if not (file.filename or "").lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="JSON 파일만 업로드 가능합니다")
    raw_bytes = await file.read()
    try:
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="유효하지 않은 JSON 파일입니다")
    if not isinstance(raw, list):
        raise HTTPException(status_code=400, detail="JSON 파일은 배열 형식이어야 합니다")

    valid_items: list[dict] = []
    skipped = 0
    for item in raw[:MAX_UPLOAD_ITEMS]:
        if not isinstance(item, dict):
            skipped += 1
            continue
        title = str(item.get("title", "")).strip()
        content = str(item.get("content", "")).strip()
        if not title or not content:
            skipped += 1
            continue
        valid_items.append({"title": title, "content": content, "source_url": item.get("source_url") or None})

    if not valid_items:
        raise HTTPException(status_code=400, detail="유효한 문서가 없습니다 (title, content 필수)")

    docs = AiOverviewService(session).bulk_create_documents(valid_items)
    job = create_job(len(docs))
    background_tasks.add_task(
        run_keyword_generation_job, job.job_id, [d.id for d in docs], system_prompt
    )
    return ApiResponse.ok({"job_id": job.job_id, "total": len(docs), "skipped": skipped})


@router.get("/documents/upload/{job_id}/progress", response_model=ApiResponse[dict])
def get_upload_progress(
    job_id: str, user: User = Depends(get_current_user)
) -> ApiResponse[dict]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ApiResponse.ok(
        {
            "job_id": job.job_id,
            "total": job.total,
            "processed": job.processed,
            "failed": job.failed,
            "status": job.status,
            "recent": job.recent,
        }
    )


# ── 복수/전체 삭제 (static — /{doc_id}보다 먼저) ──
@router.delete("/documents/batch", response_model=ApiResponse[dict])
def batch_delete_documents(
    body: BatchDeleteRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[dict]:
    if not body.ids:
        raise HTTPException(status_code=400, detail="삭제할 문서 ID가 없습니다")
    deleted = AiOverviewService(session).bulk_delete_documents(body.ids)
    return ApiResponse.ok({"deleted": deleted})


@router.delete("/documents/all", response_model=ApiResponse[dict])
def delete_all_documents(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[dict]:
    deleted = AiOverviewService(session).delete_all_documents()
    return ApiResponse.ok({"deleted": deleted})


# ── 단건 CRUD (동적 /{doc_id}) ──
@router.get("/documents", response_model=ApiResponse[DocumentListResponse])
def list_documents(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str = "",
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[DocumentListResponse]:
    items, total = AiOverviewService(session).list_documents(offset=offset, limit=limit, search=search)
    return ApiResponse.ok(DocumentListResponse(total=total, items=items))


@router.post("/documents", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
def create_document(
    body: DocumentCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[dict]:
    doc = AiOverviewService(session).create_document(
        title=body.title, content=body.content, source_url=body.source_url
    )
    return ApiResponse.ok(
        {"id": doc.id, "title": doc.title, "status": doc.status, "created_at": doc.created_at.isoformat()}
    )


@router.get("/documents/{doc_id}", response_model=ApiResponse[DocumentDetailResponse])
def get_document(
    doc_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[DocumentDetailResponse]:
    detail = AiOverviewService(session).get_document_detail(doc_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return ApiResponse.ok(detail)


@router.delete("/documents/{doc_id}", response_model=ApiResponse[None])
def delete_document(
    doc_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[None]:
    if not AiOverviewService(session).delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return ApiResponse.ok(None)


@router.post("/documents/{doc_id}/generate-keywords", response_model=ApiResponse[dict])
def generate_keywords_endpoint(
    doc_id: int,
    body: GenerateKeywordsRequest = Body(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[dict]:
    svc = AiOverviewService(session)
    if svc.get_document(doc_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        count = svc.process_document(doc_id, system_prompt=body.system_prompt if body else None)
    except Exception:
        raise HTTPException(status_code=500, detail="키워드 생성에 실패했습니다")
    return ApiResponse.ok({"doc_id": doc_id, "keyword_count": count})


@router.get("/documents/{doc_id}/keywords", response_model=ApiResponse[list[KeywordResponse]])
def list_keywords(
    doc_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[list[KeywordResponse]]:
    svc = AiOverviewService(session)
    if svc.get_document(doc_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return ApiResponse.ok(svc.get_keywords(doc_id))


@router.delete("/documents/{doc_id}/keywords/{keyword_id}", response_model=ApiResponse[None])
def delete_keyword(
    doc_id: int,
    keyword_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    if not AiOverviewService(session).delete_keyword(keyword_id):
        raise HTTPException(status_code=404, detail="Keyword not found")
    return ApiResponse.ok(None)


# ── 하이브리드 검색 (NDJSON 스트리밍 — ApiResponse 미적용) ──
@router.post("/search")
async def ai_overview_search(
    body: SearchRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    svc = AiOverviewService(session)

    async def generate():
        async for line in svc.stream_search(query, system_prompt=body.system_prompt.strip() or None):
            yield f"{line}\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
