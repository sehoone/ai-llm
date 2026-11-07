"""rag 도메인 영속 계층 (ADR-0012). 그룹/키/문서는 ORM, 임베딩(vector)은 raw SQL."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, select

from src.domains.rag.model import Document, RagGroupConfig, RagKeyConfig


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(map(str, vec)) + "]"


class RagRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── 그룹 ──
    def create_group(self, group: RagGroupConfig) -> RagGroupConfig:
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        return group

    def get_group(self, group_id: str) -> RagGroupConfig | None:
        return self.session.get(RagGroupConfig, group_id)

    def list_groups(self, user_id: int) -> list[RagGroupConfig]:
        return list(
            self.session.exec(
                select(RagGroupConfig)
                .where(RagGroupConfig.user_id == user_id)
                .order_by(RagGroupConfig.created_at.desc())
            ).all()
        )

    def save_group(self, group: RagGroupConfig) -> RagGroupConfig:
        group.updated_at = datetime.utcnow()
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        return group

    def delete_group(self, group: RagGroupConfig) -> None:
        self.session.delete(group)
        self.session.commit()

    # ── 키 ──
    def create_key(self, key: RagKeyConfig) -> RagKeyConfig:
        self.session.add(key)
        self.session.commit()
        self.session.refresh(key)
        return key

    def get_key(self, key_id: str) -> RagKeyConfig | None:
        return self.session.get(RagKeyConfig, key_id)

    def list_keys(self, user_id: int, rag_group: str | None = None) -> list[RagKeyConfig]:
        stmt = select(RagKeyConfig).where(RagKeyConfig.user_id == user_id)
        if rag_group is not None:
            stmt = stmt.where(RagKeyConfig.rag_group == rag_group)
        return list(self.session.exec(stmt.order_by(RagKeyConfig.created_at.desc())).all())

    def save_key(self, key: RagKeyConfig) -> RagKeyConfig:
        key.updated_at = datetime.utcnow()
        self.session.add(key)
        self.session.commit()
        self.session.refresh(key)
        return key

    def delete_key(self, key: RagKeyConfig) -> None:
        self.session.delete(key)
        self.session.commit()

    # ── 문서 ──
    def create_document(self, doc: Document) -> Document:
        self.session.add(doc)
        self.session.commit()
        self.session.refresh(doc)
        return doc

    def get_document(self, doc_id: int) -> Document | None:
        return self.session.get(Document, doc_id)

    def list_documents(
        self, *, rag_group: str | None = None, rag_key: str | None = None, user_id: int | None = None
    ) -> list[Document]:
        stmt = select(Document)
        if rag_group is not None:
            stmt = stmt.where(Document.rag_group == rag_group)
        if rag_key is not None:
            stmt = stmt.where(Document.rag_key == rag_key)
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        return list(self.session.exec(stmt.order_by(Document.created_at.desc())).all())

    def delete_document(self, doc: Document) -> None:
        self.delete_embeddings_by_doc(doc.id)
        self.session.delete(doc)
        self.session.commit()

    # ── 카운트 ──
    def count_keys_in_group(self, user_id: int, group_name: str) -> int:
        return len(self.list_keys(user_id, rag_group=group_name))

    def count_docs_in_group(self, rag_group: str) -> int:
        return len(self.list_documents(rag_group=rag_group))

    def count_docs_in_key(self, rag_key: str) -> int:
        return len(self.list_documents(rag_key=rag_key))

    # ── 임베딩 (raw SQL / pgvector) ──
    def insert_embeddings(
        self,
        *,
        doc_id: int,
        rag_key: str,
        rag_group: str,
        rag_type: str,
        chunks: list[str],
        vectors: list[list[float]],
        start_index: int = 0,
    ) -> int:
        inserted = 0
        for i, (chunk, vec) in enumerate(zip(chunks, vectors, strict=False)):
            self.session.execute(
                text(
                    "INSERT INTO llmonl.rag_embedding "
                    "(doc_id, rag_key, rag_group, rag_type, chunk_index, content, embedding, created_at) "
                    "VALUES (:doc_id, :rag_key, :rag_group, :rag_type, :chunk_index, :content, "
                    "CAST(:embedding AS vector), NOW())"
                ),
                {
                    "doc_id": doc_id,
                    "rag_key": rag_key,
                    "rag_group": rag_group,
                    "rag_type": rag_type,
                    "chunk_index": start_index + i,
                    "content": chunk,
                    "embedding": _vec_literal(vec),
                },
            )
            inserted += 1
        self.session.commit()
        return inserted

    def delete_embeddings_by_doc(self, doc_id: int) -> None:
        self.session.execute(
            text("DELETE FROM llmonl.rag_embedding WHERE doc_id = :doc_id"), {"doc_id": doc_id}
        )
        self.session.commit()

    def vector_search_group(
        self, *, rag_group: str, query_vector: list[float], limit: int = 5, user_id: int | None = None
    ) -> list[dict[str, Any]]:
        """rag_group 내 유사 청크 검색 (pgvector 코사인). user_id 주면 소유 문서로 제한."""
        where = "re.rag_group = :rag_group"
        params: dict[str, Any] = {
            "rag_group": rag_group,
            "q": _vec_literal(query_vector),
            "limit": limit,
        }
        if user_id is not None:
            where += " AND d.user_id = :user_id"
            params["user_id"] = user_id
        rows = self.session.execute(
            text(
                "SELECT re.id, re.doc_id, re.rag_key, re.rag_group, d.filename, re.content, "
                "re.chunk_index, 1 - (re.embedding <=> CAST(:q AS vector)) AS similarity "
                "FROM llmonl.rag_embedding re "
                "JOIN llmonl.document d ON re.doc_id = d.id "
                f"WHERE {where} "
                "ORDER BY re.embedding <=> CAST(:q AS vector) "
                "LIMIT :limit"
            ),
            params,
        ).all()
        return [
            {
                "id": r[0],
                "doc_id": r[1],
                "rag_key": r[2],
                "rag_group": r[3],
                "filename": r[4],
                "content": r[5],
                "chunk_index": r[6],
                "similarity": float(r[7]),
            }
            for r in rows
        ]
