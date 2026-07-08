"""AI Overview document management API."""

import json

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from src.ai_overview.schemas.document_schema import (
    DocumentCreateRequest,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentSummaryResponse,
    KeywordResponse,
)
from src.ai_overview.services.document_service import ai_overview_document_service
from src.ai_overview.services.upload_job import create_job, get_job, record_done
from src.auth.api.auth_api import get_current_user
from src.common.logging import logger
from src.user.models.user_model import User

router = APIRouter()

MAX_UPLOAD_ITEMS = 10_000


# ── Background task ────────────────────────────────────────────────────────────

async def _generate_keywords_background(job_id: str, doc_ids: list[int], system_prompt: str | None = None, model_name: str | None = None) -> None:
    for doc_id in doc_ids:
        try:
            keywords = await ai_overview_document_service.generate_keywords(doc_id, system_prompt=system_prompt, model_name=model_name)
            doc = await ai_overview_document_service.get_document(doc_id)
            record_done(
                job_id,
                success=True,
                doc_info={
                    "id": doc_id,
                    "title": doc.title if doc else "",
                    "keyword_count": len(keywords),
                },
            )
        except Exception as e:
            logger.error("background_keyword_gen_failed", doc_id=doc_id, error=str(e))
            record_done(job_id, success=False)


# ── JSON 파일 업로드 (static 경로 — /{doc_id} 보다 먼저 등록) ──────────────────

@router.post("/upload")
async def upload_documents_json(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    system_prompt: str | None = Form(default=None),
    model: str | None = Form(default=None),
    _user: User = Depends(get_current_user),
):
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
        valid_items.append(
            {
                "title": title,
                "content": content,
                "source_url": item.get("source_url") or None,
            }
        )

    if not valid_items:
        raise HTTPException(status_code=400, detail="유효한 문서가 없습니다 (title, content 필수)")

    docs = await ai_overview_document_service.bulk_create_documents(valid_items)
    job = create_job(len(docs))
    background_tasks.add_task(_generate_keywords_background, job.job_id, [d.id for d in docs], system_prompt, model or None)

    logger.info(
        "ai_overview_upload_started",
        total=len(docs),
        skipped=skipped,
        job_id=job.job_id,
    )
    return {"job_id": job.job_id, "total": len(docs), "skipped": skipped}


@router.get("/upload/{job_id}/progress")
async def get_upload_progress(
    request: Request,
    job_id: str,
    _user: User = Depends(get_current_user),
):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "total": job.total,
        "processed": job.processed,
        "failed": job.failed,
        "status": job.status,
        "recent": job.recent,
    }


# ── 복수 삭제 (static 경로 — /{doc_id} 보다 먼저 등록) ───────────────────────────

class BatchDeleteRequest(BaseModel):
    ids: list[int]


class GenerateKeywordsRequest(BaseModel):
    system_prompt: str | None = None
    model: str | None = None


@router.delete("/batch")
async def batch_delete_documents(
    request: Request,
    body: BatchDeleteRequest,
    _user: User = Depends(get_current_user),
):
    if not body.ids:
        raise HTTPException(status_code=400, detail="삭제할 문서 ID가 없습니다")
    deleted = await ai_overview_document_service.bulk_delete_documents(body.ids)
    logger.info("ai_overview_batch_delete_api", requested=len(body.ids), deleted=deleted)
    return {"deleted": deleted}


# ── 전체 삭제 (static 경로 — /{doc_id} 보다 먼저 등록) ───────────────────────────

@router.delete("/all")
async def delete_all_documents(
    request: Request,
    _user: User = Depends(get_current_user),
):
    deleted = await ai_overview_document_service.delete_all_documents()
    logger.info("ai_overview_delete_all_api", deleted=deleted)
    return {"deleted": deleted}


# ── 단건 CRUD (동적 경로 /{doc_id} — 위 static 라우트 이후 등록) ────────────────

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    request: Request,
    offset: int = 0,
    limit: int = 20,
    search: str = "",
    _user: User = Depends(get_current_user),
):
    docs, total = await ai_overview_document_service.list_documents(
        offset=offset, limit=limit, search=search
    )
    items = []
    for doc in docs:
        kw_count = await ai_overview_document_service.count_keywords(doc.id)
        items.append(
            DocumentSummaryResponse(
                id=doc.id,
                title=doc.title,
                source_url=doc.source_url,
                status=doc.status,
                keyword_count=kw_count,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
        )
    return DocumentListResponse(total=total, items=items)


@router.post("", status_code=201)
async def create_document(
    request: Request,
    body: DocumentCreateRequest,
    _user: User = Depends(get_current_user),
):
    doc = await ai_overview_document_service.create_document(
        title=body.title.strip(),
        content=body.content,
        source_url=body.source_url,
    )
    return {"id": doc.id, "title": doc.title, "status": doc.status, "created_at": doc.created_at}


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    request: Request,
    doc_id: int,
    _user: User = Depends(get_current_user),
):
    doc = await ai_overview_document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    keywords = await ai_overview_document_service.get_keywords(doc_id)
    return DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        content=doc.content,
        source_url=doc.source_url,
        status=doc.status,
        keyword_count=len(keywords),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        keywords=[
            KeywordResponse(id=k.id, keyword=k.keyword, keyword_type=k.keyword_type, created_at=k.created_at)
            for k in keywords
        ],
    )


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    request: Request,
    doc_id: int,
    _user: User = Depends(get_current_user),
):
    ok = await ai_overview_document_service.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/{doc_id}/generate-keywords")
async def generate_keywords(
    request: Request,
    doc_id: int,
    body: GenerateKeywordsRequest = Body(default=None),
    _user: User = Depends(get_current_user),
):
    doc = await ai_overview_document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        system_prompt = body.system_prompt if body else None
        model_name = body.model if body else None
        keywords = await ai_overview_document_service.generate_keywords(doc_id, system_prompt=system_prompt, model_name=model_name)
        return {"doc_id": doc_id, "keyword_count": len(keywords)}
    except Exception as e:
        logger.error("generate_keywords_api_failed", doc_id=doc_id, error=str(e))
        raise HTTPException(status_code=500, detail="키워드 생성에 실패했습니다")


@router.get("/{doc_id}/keywords", response_model=list[KeywordResponse])
async def list_keywords(
    request: Request,
    doc_id: int,
    _user: User = Depends(get_current_user),
):
    doc = await ai_overview_document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    keywords = await ai_overview_document_service.get_keywords(doc_id)
    return [
        KeywordResponse(id=k.id, keyword=k.keyword, keyword_type=k.keyword_type, created_at=k.created_at)
        for k in keywords
    ]


@router.delete("/{doc_id}/keywords/{keyword_id}", status_code=204)
async def delete_keyword(
    request: Request,
    doc_id: int,
    keyword_id: int,
    _user: User = Depends(get_current_user),
):
    ok = await ai_overview_document_service.delete_keyword(keyword_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Keyword not found")
