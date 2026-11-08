"""ai_overview 도메인 서비스.

도메인 책임(ADR-0005): HTTP 경계·관계형 영속·인가·오케스트레이션. AI 연산(키워드 추출·답변
스트리밍)은 engine/ai_overview에, 청킹·임베딩은 engine/rag에 위임한다. LLM 선택은 전적으로
`llm_resource` 테이블에서 해석해 `LlmConfig`로 주입(engine은 DB 미조회).

검색은 하이브리드: trgm 키워드 매칭 + pgvector 코사인을 RRF로 융합. 임베딩 리소스가 없으면
벡터 축을 건너뛰고 trgm 단독으로 degrade한다(검색을 막지 않음).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlmodel import Session

from src.core.config import settings
from src.core.db import engine as _db_engine
from src.domains.ai_overview.model import AiOverviewDocument, AiOverviewKeyword
from src.domains.ai_overview.repository import AiOverviewRepository
from src.domains.ai_overview.schema import (
    DocumentDetailResponse,
    DocumentSummaryResponse,
    KeywordResponse,
)
from src.domains.ai_overview.upload_job import record_done
from src.domains.llm_resource.model import LlmResource
from src.domains.llm_resource.repository import LlmResourceRepository
from src.engine.ai_overview import extract_query_keywords, generate_keywords, stream_answer
from src.engine.llm.config import LlmConfig
from src.engine.rag import chunk_text, embed_query, embed_texts

logger = logging.getLogger(__name__)

_EMBED_BATCH = 16
_RRF_K = 60
_SEARCH_TOP_N = 5
_VECTOR_CANDIDATES = 10


def _config_from_resource(r: LlmResource) -> LlmConfig:
    """llm_resource 행 → LlmConfig (azure는 deployment_name을 model로)."""
    model = r.deployment_name if r.provider == "azure" else (r.model_name or r.name)
    return LlmConfig(
        provider=r.provider,
        model=model or r.name,
        api_key=r.api_key or None,
        api_base=r.api_base or None,
        api_version=r.api_version or None,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens or None,
    )


def _nd(obj: Any) -> str:
    """NDJSON 한 줄 — 한글을 이스케이프하지 않는다(chat `_sse` 컨벤션 일치)."""
    return json.dumps(obj, ensure_ascii=False)


def _rrf_fuse(
    rankings: list[list[dict[str, Any]]], *, limit: int = _SEARCH_TOP_N, k: int = _RRF_K
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion — 각 랭킹(점수 내림차순)의 rank만으로 결합(점수 정규화 불필요).

    score(d) = Σ 1/(k + rank_i(d)). 같은 문서가 여러 랭킹에 있으면 처음 본 item을 유지.
    """
    merged: dict[int, dict[str, Any]] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            doc_id = item["id"]
            entry = merged.get(doc_id)
            if entry is None:
                entry = {"item": item, "score": 0.0}
                merged[doc_id] = entry
            entry["score"] += 1.0 / (k + rank + 1)
    ordered = sorted(merged.values(), key=lambda e: e["score"], reverse=True)
    out: list[dict[str, Any]] = []
    for e in ordered[:limit]:
        item = dict(e["item"])
        item["score"] = e["score"]
        out.append(item)
    return out


class AiOverviewService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = AiOverviewRepository(session)

    # ── LLM/임베딩 설정 해석 ──
    def _chat_config(self) -> LlmConfig | None:
        r = LlmResourceRepository(self.session).default_chat_model()
        return _config_from_resource(r) if r is not None else None

    def _embedding_config(self) -> LlmConfig | None:
        r = LlmResourceRepository(self.session).default_embedding_model()
        return _config_from_resource(r) if r is not None else None

    # ── 문서 CRUD ──
    def get_document(self, doc_id: int) -> AiOverviewDocument | None:
        return self.repo.get_document(doc_id)

    def create_document(self, *, title: str, content: str, source_url: str | None) -> AiOverviewDocument:
        return self.repo.create_document(
            AiOverviewDocument(title=title.strip(), content=content, source_url=source_url)
        )

    def list_documents(self, *, offset: int, limit: int, search: str) -> tuple[list[DocumentSummaryResponse], int]:
        docs, total = self.repo.list_documents(offset=offset, limit=limit, search=search)
        items = [
            DocumentSummaryResponse.from_model(d, keyword_count=self.repo.count_keywords(d.id))
            for d in docs
        ]
        return items, total

    def get_document_detail(self, doc_id: int) -> DocumentDetailResponse | None:
        doc = self.repo.get_document(doc_id)
        if doc is None:
            return None
        keywords = self.repo.get_keywords(doc_id)
        return DocumentDetailResponse(
            id=doc.id,
            title=doc.title,
            content=doc.content,
            source_url=doc.source_url,
            status=doc.status,
            keyword_count=len(keywords),
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            keywords=[KeywordResponse.from_model(k) for k in keywords],
        )

    def delete_document(self, doc_id: int) -> bool:
        return self.repo.delete_document(doc_id)

    def delete_all_documents(self) -> int:
        return self.repo.delete_all_documents()

    def bulk_delete_documents(self, ids: list[int]) -> int:
        return self.repo.bulk_delete_documents(ids)

    def bulk_create_documents(self, items: list[dict]) -> list[AiOverviewDocument]:
        return self.repo.bulk_create_documents(items)

    # ── 키워드 ──
    def get_keywords(self, doc_id: int) -> list[KeywordResponse]:
        return [KeywordResponse.from_model(k) for k in self.repo.get_keywords(doc_id)]

    def delete_keyword(self, keyword_id: int) -> bool:
        return self.repo.delete_keyword(keyword_id)

    # ── 문서 처리: 키워드 추출 + 임베딩 (동기, 블로킹) ──
    def process_document(self, doc_id: int, *, system_prompt: str | None = None) -> int:
        """문서에서 키워드/동의어 추출(교체) + 청크 임베딩(교체). 반환: 저장된 키워드 수.

        실패 시 status='error'로 표시하고 예외 전파. 임베딩 리소스가 없으면 벡터 생성만 건너뛴다.
        """
        doc = self.repo.get_document(doc_id)
        if doc is None:
            raise ValueError(f"Document {doc_id} not found")
        chat_cfg = self._chat_config()
        if chat_cfg is None:
            self.repo.update_status(doc_id, "error")
            raise ValueError("활성 chat LLM 리소스가 없습니다")

        self.repo.update_status(doc_id, "processing")
        try:
            extraction = generate_keywords(doc.title, doc.content, chat_cfg, system_prompt=system_prompt)
            rows: list[AiOverviewKeyword] = []
            for kw in extraction.keywords:
                if not kw.strip():
                    continue
                rows.append(AiOverviewKeyword(document_id=doc_id, keyword=kw.strip(), keyword_type="keyword"))
                for syn in extraction.synonyms.get(kw, []):
                    if syn.strip():
                        rows.append(
                            AiOverviewKeyword(document_id=doc_id, keyword=syn.strip(), keyword_type="synonym")
                        )
            saved = self.repo.replace_keywords(doc_id, rows)
            self._embed_document(doc_id, doc.content)
            self.repo.update_status(doc_id, "ready")
            logger.info("ai_overview_document_processed doc_id=%s keywords=%s", doc_id, len(saved))
            return len(saved)
        except Exception:
            self.repo.update_status(doc_id, "error")
            logger.exception("ai_overview_document_processing_failed doc_id=%s", doc_id)
            raise

    def _embed_document(self, doc_id: int, content: str) -> int:
        """문서 본문을 청킹·임베딩해 벡터 축에 저장. 임베딩 리소스 없으면 건너뜀(0)."""
        emb_cfg = self._embedding_config()
        if emb_cfg is None:
            logger.info("ai_overview_embedding_skipped doc_id=%s (no embedding resource)", doc_id)
            return 0
        chunks = chunk_text(content)
        vectors: list[list[float]] = []
        for i in range(0, len(chunks), _EMBED_BATCH):
            vectors.extend(embed_texts(chunks[i : i + _EMBED_BATCH], emb_cfg))
        return self.repo.replace_embeddings(doc_id, chunks, vectors)

    # ── 하이브리드 검색 (NDJSON 스트리밍) ──
    async def stream_search(self, query: str, *, system_prompt: str | None = None):
        """질문 키워드 추출 → trgm·벡터 병렬 검색 → RRF 융합 → 근거 기반 LLM 답변 스트리밍.

        yield는 NDJSON 한 줄(개행은 api가 붙임):
          {"type":"keywords","data":[...]} / {"type":"sources","data":[...]}
          {"type":"chunk","data":"..."} / {"type":"error","data":"..."}
        """
        chat_cfg = self._chat_config()
        if chat_cfg is None:
            yield _nd({"type": "error", "data": "활성 chat LLM 리소스가 없습니다."})
            return

        # 1. 질문 키워드 추출 (블로킹 LLM → thread)
        keywords = await asyncio.to_thread(extract_query_keywords, query, chat_cfg)
        yield _nd({"type": "keywords", "data": keywords})

        # 2a. trgm 축
        trgm = await asyncio.to_thread(self.repo.trgm_search, keywords)

        # 2b. 벡터 축 (임베딩 리소스 있을 때만 — 없으면 trgm 단독 degrade)
        vector: list[dict[str, Any]] = []
        emb_cfg = self._embedding_config()
        if emb_cfg is not None:
            try:
                qv = await asyncio.to_thread(embed_query, query, emb_cfg)
                vector = await asyncio.to_thread(self.repo.vector_search, qv, _VECTOR_CANDIDATES)
            except Exception:
                logger.exception("ai_overview_vector_search_failed — trgm only")

        # 3. RRF 융합 (순수)
        fused = _rrf_fuse([trgm, vector])
        logger.info(
            "ai_overview_search query=%r keywords=%s trgm=%s vector=%s fused=%s",
            query, keywords, len(trgm), len(vector), len(fused),
        )

        sources = [
            {"id": d["id"], "title": d["title"], "source_url": d.get("source_url"), "score": d["score"]}
            for d in fused
        ]
        yield _nd({"type": "sources", "data": sources})

        # 4. 근거 기반 답변 스트리밍
        try:
            async for chunk in stream_answer(query, fused, chat_cfg, system_prompt=system_prompt):
                if chunk:
                    yield _nd({"type": "chunk", "data": chunk})
        except Exception:
            logger.exception("ai_overview_answer_stream_failed")
            yield _nd({"type": "error", "data": "답변 생성 중 오류가 발생했습니다."})


def run_keyword_generation_job(
    job_id: str, doc_ids: list[int], system_prompt: str | None = None
) -> None:
    """업로드 후 백그라운드 키워드/임베딩 생성. 요청 세션과 분리된 자체 세션을 연다."""
    for doc_id in doc_ids:
        try:
            with Session(_db_engine) as session:
                svc = AiOverviewService(session)
                count = svc.process_document(doc_id, system_prompt=system_prompt)
                doc = svc.get_document(doc_id)
                record_done(
                    job_id,
                    success=True,
                    doc_info={"id": doc_id, "title": doc.title if doc else "", "keyword_count": count},
                )
        except Exception:
            logger.exception("ai_overview_background_job_failed doc_id=%s", doc_id)
            record_done(job_id, success=False)
