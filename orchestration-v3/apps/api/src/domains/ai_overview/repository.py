"""ai_overview 영속 계층. 문서/키워드는 ORM, 임베딩·trgm/벡터 검색은 raw SQL (rag 규약 계승)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy import text as sql_text
from sqlmodel import Session, delete, select

from src.domains.ai_overview.model import AiOverviewDocument, AiOverviewKeyword

_TRGM_THRESHOLD = 0.3
_TRGM_MAX_PER_KEYWORD = 3


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(map(str, vec)) + "]"


class AiOverviewRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── 문서 ──
    def create_document(self, doc: AiOverviewDocument) -> AiOverviewDocument:
        self.session.add(doc)
        self.session.commit()
        self.session.refresh(doc)
        return doc

    def bulk_create_documents(self, items: list[dict]) -> list[AiOverviewDocument]:
        """100건 단위 배치 insert."""
        BATCH = 100
        created: list[AiOverviewDocument] = []
        for i in range(0, len(items), BATCH):
            batch = items[i : i + BATCH]
            docs = [
                AiOverviewDocument(
                    title=it["title"], content=it["content"], source_url=it.get("source_url")
                )
                for it in batch
            ]
            self.session.add_all(docs)
            self.session.commit()
            for d in docs:
                self.session.refresh(d)
            created.extend(docs)
        return created

    def get_document(self, doc_id: int) -> AiOverviewDocument | None:
        return self.session.get(AiOverviewDocument, doc_id)

    def list_documents(
        self, *, offset: int = 0, limit: int = 20, search: str = ""
    ) -> tuple[list[AiOverviewDocument], int]:
        base = select(AiOverviewDocument)
        count_base = select(func.count(AiOverviewDocument.id))
        if search:
            pattern = f"%{search}%"
            base = base.where(AiOverviewDocument.title.ilike(pattern))
            count_base = count_base.where(AiOverviewDocument.title.ilike(pattern))
        total = self.session.exec(count_base).one()
        docs = list(
            self.session.exec(
                base.order_by(AiOverviewDocument.created_at.desc()).offset(offset).limit(limit)
            ).all()
        )
        return docs, total

    def update_status(self, doc_id: int, status: str) -> None:
        doc = self.session.get(AiOverviewDocument, doc_id)
        if doc:
            doc.status = status
            doc.updated_at = datetime.utcnow()
            self.session.add(doc)
            self.session.commit()

    def delete_document(self, doc_id: int) -> bool:
        doc = self.session.get(AiOverviewDocument, doc_id)
        if not doc:
            return False
        self._delete_doc_children(doc_id)
        self.session.delete(doc)
        self.session.commit()
        return True

    def delete_all_documents(self) -> int:
        count = self.session.exec(select(func.count(AiOverviewDocument.id))).one()
        self.session.exec(delete(AiOverviewKeyword))
        self._delete_all_embeddings()
        self.session.exec(delete(AiOverviewDocument))
        self.session.commit()
        return count

    def bulk_delete_documents(self, ids: list[int]) -> int:
        count = 0
        for doc_id in ids:
            doc = self.session.get(AiOverviewDocument, doc_id)
            if doc:
                self._delete_doc_children(doc_id)
                self.session.delete(doc)
                count += 1
        self.session.commit()
        return count

    def _delete_doc_children(self, doc_id: int) -> None:
        """키워드·임베딩 정리 (FK CASCADE 없음). commit은 호출부에서."""
        self.session.exec(delete(AiOverviewKeyword).where(AiOverviewKeyword.document_id == doc_id))
        self.session.execute(
            sql_text("DELETE FROM llmonl.ai_overview_embedding WHERE document_id = :d"),
            {"d": doc_id},
        )

    # ── 키워드 ──
    def get_keywords(self, doc_id: int) -> list[AiOverviewKeyword]:
        return list(
            self.session.exec(
                select(AiOverviewKeyword)
                .where(AiOverviewKeyword.document_id == doc_id)
                .order_by(AiOverviewKeyword.keyword_type, AiOverviewKeyword.keyword)
            ).all()
        )

    def count_keywords(self, doc_id: int) -> int:
        return self.session.exec(
            select(func.count(AiOverviewKeyword.id)).where(AiOverviewKeyword.document_id == doc_id)
        ).one()

    def delete_keyword(self, keyword_id: int) -> bool:
        kw = self.session.get(AiOverviewKeyword, keyword_id)
        if not kw:
            return False
        self.session.delete(kw)
        self.session.commit()
        return True

    def replace_keywords(self, doc_id: int, rows: list[AiOverviewKeyword]) -> list[AiOverviewKeyword]:
        """문서의 키워드를 전량 교체."""
        self.session.exec(delete(AiOverviewKeyword).where(AiOverviewKeyword.document_id == doc_id))
        self.session.commit()
        for r in rows:
            self.session.add(r)
        self.session.commit()
        for r in rows:
            self.session.refresh(r)
        return rows

    # ── 임베딩 (raw SQL / pgvector) ──
    def replace_embeddings(
        self, doc_id: int, chunks: list[str], vectors: list[list[float]]
    ) -> int:
        self.session.execute(
            sql_text("DELETE FROM llmonl.ai_overview_embedding WHERE document_id = :d"),
            {"d": doc_id},
        )
        inserted = 0
        for i, (chunk, vec) in enumerate(zip(chunks, vectors, strict=False)):
            self.session.execute(
                sql_text(
                    "INSERT INTO llmonl.ai_overview_embedding "
                    "(document_id, chunk_index, content, embedding, created_at) "
                    "VALUES (:d, :i, :c, CAST(:e AS vector), NOW())"
                ),
                {"d": doc_id, "i": i, "c": chunk, "e": _vec_literal(vec)},
            )
            inserted += 1
        self.session.commit()
        return inserted

    def _delete_all_embeddings(self) -> None:
        self.session.execute(sql_text("TRUNCATE llmonl.ai_overview_embedding"))

    # ── 검색 (하이브리드의 두 축) ──
    def trgm_search(self, keywords: list[str]) -> list[dict[str, Any]]:
        """키워드별 trgm 유사도 검색 → 문서별 best score로 병합. status='ready'만."""
        sql = sql_text(
            "SELECT d.id, d.title, d.content, d.source_url, "
            "MAX(similarity(k.keyword, :q)) AS score "
            "FROM llmonl.ai_overview_document d "
            "JOIN llmonl.ai_overview_keyword k ON k.document_id = d.id "
            "WHERE similarity(k.keyword, :q) >= :threshold AND d.status = 'ready' "
            "GROUP BY d.id, d.title, d.content, d.source_url "
            "ORDER BY score DESC LIMIT :lim"
        )
        seen: dict[int, dict[str, Any]] = {}
        for kw in keywords:
            rows = self.session.execute(
                sql, {"q": kw, "threshold": _TRGM_THRESHOLD, "lim": _TRGM_MAX_PER_KEYWORD}
            ).fetchall()
            for doc_id, title, content, source_url, score in rows:
                score = float(score)
                if doc_id not in seen or score > seen[doc_id]["score"]:
                    seen[doc_id] = {
                        "id": doc_id,
                        "title": title,
                        "content": content,
                        "source_url": source_url,
                        "score": score,
                    }
        return sorted(seen.values(), key=lambda x: x["score"], reverse=True)

    def vector_search(self, query_vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
        """문서 청크 코사인 검색 → 문서별 best score로 병합. status='ready'만."""
        rows = self.session.execute(
            sql_text(
                "SELECT d.id, d.title, d.content, d.source_url, "
                "MAX(1 - (e.embedding <=> CAST(:q AS vector))) AS score "
                "FROM llmonl.ai_overview_embedding e "
                "JOIN llmonl.ai_overview_document d ON e.document_id = d.id "
                "WHERE d.status = 'ready' "
                "GROUP BY d.id, d.title, d.content, d.source_url "
                "ORDER BY score DESC LIMIT :lim"
            ),
            {"q": _vec_literal(query_vector), "lim": limit},
        ).fetchall()
        return [
            {
                "id": doc_id,
                "title": title,
                "content": content,
                "source_url": source_url,
                "score": float(score),
            }
            for doc_id, title, content, source_url, score in rows
        ]
