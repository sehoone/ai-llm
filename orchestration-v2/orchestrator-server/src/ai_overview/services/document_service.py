"""AI Overview document and keyword management service."""

import json
from datetime import datetime, UTC
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session, select, func

from src.ai_overview.models.document_model import AiOverviewDocument
from src.ai_overview.models.keyword_model import AiOverviewKeyword
from src.common.logging import logger
from src.common.services.database import database_service
from src.common.services.llm import llm_service

_KEYWORD_SYSTEM = """문서에서 검색에 사용될 핵심 키워드와 동의어를 추출하세요.

추출 기준:
- 핵심 명사, 업무 용어, 고유 명사 중심
- 동의어는 같은 개념의 다른 표현(약어, 한자어, 영문 혼용 등)

반드시 다음 JSON 형식만 반환하세요 (설명 없이):
{
  "keywords": ["키워드1", "키워드2"],
  "synonyms": {
    "키워드1": ["동의어A", "동의어B"],
    "키워드2": ["동의어C"]
  }
}"""


class AiOverviewDocumentService:
    def __init__(self):
        self.db = database_service

    def _session(self) -> Session:
        return Session(self.db.engine)

    async def bulk_create_documents(self, items: list[dict]) -> list[AiOverviewDocument]:
        """Bulk insert documents in batches of 100."""
        BATCH_SIZE = 100
        created: list[AiOverviewDocument] = []
        for i in range(0, len(items), BATCH_SIZE):
            batch = items[i : i + BATCH_SIZE]
            with self._session() as session:
                docs = [
                    AiOverviewDocument(
                        title=item["title"],
                        content=item["content"],
                        source_url=item.get("source_url"),
                    )
                    for item in batch
                ]
                session.add_all(docs)
                session.commit()
                for doc in docs:
                    session.refresh(doc)
                created.extend(docs)
        logger.info("ai_overview_bulk_created", count=len(created))
        return created

    async def create_document(
        self, title: str, content: str, source_url: Optional[str] = None
    ) -> AiOverviewDocument:
        with self._session() as session:
            doc = AiOverviewDocument(title=title, content=content, source_url=source_url)
            session.add(doc)
            session.commit()
            session.refresh(doc)
            logger.info("ai_overview_document_created", doc_id=doc.id, title=title)
            return doc

    async def list_documents(
        self, offset: int = 0, limit: int = 20, search: str = ""
    ) -> tuple[list[AiOverviewDocument], int]:
        with self._session() as session:
            base = select(AiOverviewDocument)
            count_base = select(func.count(AiOverviewDocument.id))
            if search:
                pattern = f"%{search}%"
                base = base.where(AiOverviewDocument.title.ilike(pattern))
                count_base = count_base.where(AiOverviewDocument.title.ilike(pattern))
            total = session.exec(count_base).one()
            docs = list(
                session.exec(
                    base.order_by(AiOverviewDocument.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                ).all()
            )
            return docs, total

    async def get_document(self, doc_id: int) -> Optional[AiOverviewDocument]:
        with self._session() as session:
            return session.get(AiOverviewDocument, doc_id)

    async def delete_document(self, doc_id: int) -> bool:
        with self._session() as session:
            doc = session.get(AiOverviewDocument, doc_id)
            if not doc:
                return False
            session.delete(doc)
            session.commit()
            logger.info("ai_overview_document_deleted", doc_id=doc_id)
            return True

    async def bulk_delete_documents(self, ids: list[int]) -> int:
        with self._session() as session:
            count = 0
            for doc_id in ids:
                doc = session.get(AiOverviewDocument, doc_id)
                if doc:
                    session.delete(doc)
                    count += 1
            session.commit()
            logger.info("ai_overview_bulk_deleted", count=count)
            return count

    async def get_keywords(self, doc_id: int) -> list[AiOverviewKeyword]:
        with self._session() as session:
            return list(
                session.exec(
                    select(AiOverviewKeyword)
                    .where(AiOverviewKeyword.document_id == doc_id)
                    .order_by(AiOverviewKeyword.keyword_type, AiOverviewKeyword.keyword)
                ).all()
            )

    async def count_keywords(self, doc_id: int) -> int:
        with self._session() as session:
            return session.exec(
                select(func.count(AiOverviewKeyword.id)).where(AiOverviewKeyword.document_id == doc_id)
            ).one()

    async def delete_keyword(self, keyword_id: int) -> bool:
        with self._session() as session:
            kw = session.get(AiOverviewKeyword, keyword_id)
            if not kw:
                return False
            session.delete(kw)
            session.commit()
            return True

    def _update_status(self, doc_id: int, status: str) -> None:
        with self._session() as session:
            doc = session.get(AiOverviewDocument, doc_id)
            if doc:
                doc.status = status
                doc.updated_at = datetime.now(UTC)
                session.add(doc)
                session.commit()

    def _parse_llm_json(self, raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    async def generate_keywords(self, doc_id: int) -> list[AiOverviewKeyword]:
        """Extract keywords and synonyms from document content via LLM."""
        doc = await self.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        self._update_status(doc_id, "processing")

        try:
            response = await llm_service.call(
                messages=[
                    SystemMessage(content=_KEYWORD_SYSTEM),
                    HumanMessage(content=f"문서 제목: {doc.title}\n\n문서 내용:\n{doc.content[:8000]}"),
                ],
                model_name="gpt-4o-mini",
            )

            raw = response.content
            if isinstance(raw, list):
                raw = " ".join(
                    b.get("text", "") if isinstance(b, dict) else str(b) for b in raw
                )

            data = self._parse_llm_json(raw)
            keywords: list[str] = data.get("keywords", [])
            synonyms: dict[str, list[str]] = data.get("synonyms", {})

            # Replace existing keywords
            with self._session() as session:
                existing = session.exec(
                    select(AiOverviewKeyword).where(AiOverviewKeyword.document_id == doc_id)
                ).all()
                for kw in existing:
                    session.delete(kw)
                session.commit()

            saved: list[AiOverviewKeyword] = []
            with self._session() as session:
                for kw_text in keywords:
                    if not kw_text.strip():
                        continue
                    kw = AiOverviewKeyword(
                        document_id=doc_id,
                        keyword=kw_text.strip(),
                        keyword_type="keyword",
                    )
                    session.add(kw)
                    saved.append(kw)
                    for syn in synonyms.get(kw_text, []):
                        if not syn.strip():
                            continue
                        s = AiOverviewKeyword(
                            document_id=doc_id,
                            keyword=syn.strip(),
                            keyword_type="synonym",
                        )
                        session.add(s)
                        saved.append(s)
                session.commit()
                for item in saved:
                    session.refresh(item)

            self._update_status(doc_id, "ready")
            logger.info("ai_overview_keywords_generated", doc_id=doc_id, count=len(saved))
            return saved

        except Exception as e:
            self._update_status(doc_id, "error")
            logger.error("ai_overview_keyword_generation_failed", doc_id=doc_id, error=str(e))
            raise


ai_overview_document_service = AiOverviewDocumentService()
