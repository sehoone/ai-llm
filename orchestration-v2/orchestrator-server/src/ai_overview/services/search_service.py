"""AI Overview search service using pg_trgm."""

import asyncio
import json
from typing import AsyncGenerator, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text
from sqlmodel import Session

from src.common.config import settings
from src.common.logging import logger
from src.common.services.database import database_service
from src.common.services.llm import llm_service

SIMILARITY_THRESHOLD = 0.3
MAX_DOCS_PER_KEYWORD = 3
MAX_CONTEXT_DOCS = 5

_KEYWORD_EXTRACT_SYSTEM = """사용자 질문에서 검색 키워드를 추출하세요.
핵심 명사와 핵심 개념만 추출하여 2~6개 키워드를 반환하세요.

반드시 다음 JSON 형식만 반환하세요:
{"keywords": ["키워드1", "키워드2"]}"""

_OVERVIEW_SYSTEM = """당신은 사내 AI Overview 어시스턴트입니다.
사용자 질문에 대해 검색된 사내 문서를 기반으로 정확하고 유용한 답변을 제공하세요.

규칙:
- 검색된 문서가 있으면 해당 내용 기반으로 답변하고 출처를 [문서명]으로 표시하세요
- 문서가 없거나 관련 내용이 없으면 일반 지식으로 답변하되 "사내 데이터 없음"을 명시하세요
- 답변은 간결하고 구조화되게 작성하세요 (마크다운 사용)"""


class AiOverviewSearchService:
    def __init__(self):
        self.db = database_service

    async def _extract_keywords(self, query: str) -> list[str]:
        try:
            response = await llm_service.call(
                messages=[
                    SystemMessage(content=_KEYWORD_EXTRACT_SYSTEM),
                    HumanMessage(content=query),
                ],
                model_name="gpt-4o-mini",
            )
            raw = response.content
            if isinstance(raw, list):
                raw = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            keywords = [k.strip() for k in data.get("keywords", []) if k.strip()]
            return keywords or [query]
        except Exception as e:
            logger.warning("ai_overview_keyword_extract_failed", error=str(e))
            return [query]

    def _trgm_search_sync(self, keywords: list[str]) -> list[dict]:
        """Run pg_trgm search for all keywords and merge by best score."""
        schema = settings.POSTGRES_SCHEMA
        sql = text(f"""
            SELECT d.id, d.title, d.content, d.source_url,
                   MAX(similarity(k.keyword, :q)) AS score
            FROM {schema}.ai_overview_document d
            JOIN {schema}.ai_overview_keyword k ON k.document_id = d.id
            WHERE similarity(k.keyword, :q) >= :threshold
              AND d.status = 'ready'
            GROUP BY d.id, d.title, d.content, d.source_url
            ORDER BY score DESC
            LIMIT :lim
        """)

        seen: dict[int, dict] = {}
        with Session(self.db.engine) as session:
            for kw in keywords:
                rows = session.execute(
                    sql,
                    {"q": kw, "threshold": SIMILARITY_THRESHOLD, "lim": MAX_DOCS_PER_KEYWORD},
                ).fetchall()
                for row in rows:
                    doc_id, title, content, source_url, score = row
                    score = float(score)
                    if doc_id not in seen or score > seen[doc_id]["score"]:
                        seen[doc_id] = {
                            "id": doc_id,
                            "title": title,
                            "content": content,
                            "source_url": source_url,
                            "score": score,
                        }

        return sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:MAX_CONTEXT_DOCS]

    async def stream_search(
        self, query: str, model: str = "gpt-4o-mini", system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Keyword extraction → pg_trgm search → streaming LLM answer.

        Yields NDJSON lines:
          {"type": "keywords", "data": [...]}
          {"type": "sources",  "data": [...]}
          {"type": "chunk",    "data": "..."}
          {"type": "error",    "data": "..."}
        """
        # 1. Extract search keywords
        keywords = await self._extract_keywords(query)
        logger.info("ai_overview_search", query=query, keywords=keywords)
        yield json.dumps({"type": "keywords", "data": keywords})

        # 2. pg_trgm search (sync DB → thread)
        matched_docs = await asyncio.to_thread(self._trgm_search_sync, keywords)
        logger.info("ai_overview_matched", query=query, doc_count=len(matched_docs))

        sources = [
            {"id": d["id"], "title": d["title"], "source_url": d["source_url"], "score": d["score"]}
            for d in matched_docs
        ]
        yield json.dumps({"type": "sources", "data": sources})

        # 3. Build context
        context_parts = [f"[{d['title']}]\n{d['content'][:2000]}" for d in matched_docs]
        context_str = "\n\n---\n\n".join(context_parts) if context_parts else "관련 사내 문서 없음"
        user_msg = f"질문: {query}\n\n사내 문서:\n{context_str}"

        # 4. Stream LLM answer (사용자 프롬프트 우선, 없으면 기본값)
        effective_prompt = system_prompt if system_prompt else _OVERVIEW_SYSTEM
        try:
            async for chunk in llm_service.astream(
                messages=[SystemMessage(content=effective_prompt), HumanMessage(content=user_msg)],
                model_name=model,
            ):
                content = chunk.content
                if isinstance(content, list):
                    content = "".join(
                        b.get("text", "") if isinstance(b, dict) and b.get("type") == "text"
                        else (b if isinstance(b, str) else "")
                        for b in content
                    )
                if content:
                    yield json.dumps({"type": "chunk", "data": str(content)})
        except Exception as e:
            logger.error("ai_overview_llm_stream_failed", error=str(e))
            yield json.dumps({"type": "error", "data": "답변 생성 중 오류가 발생했습니다."})


ai_overview_search_service = AiOverviewSearchService()
