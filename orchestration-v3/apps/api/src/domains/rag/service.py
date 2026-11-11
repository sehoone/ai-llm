"""rag 도메인 서비스 (ADR-0012). 수집·검색·그룹/키 CRUD.

AI 연산(청킹·임베딩)은 engine/rag에 위임. 임베딩 provider 설정은 embedding 타입 llm_resource를
해석해 `LlmConfig`로 주입(ADR-0005 — engine은 DB 미조회).
"""

from __future__ import annotations

import logging

from sqlmodel import Session

from src.core.exceptions import NotFoundError, ValidationError
from src.domains.rag.model import Document, RagGroupConfig, RagKeyConfig
from src.domains.rag.repository import RagRepository
from src.domains.rag.schema import (
    DocumentUploadRequest,
    GroupCreateRequest,
    GroupUpdateRequest,
    KeyCreateRequest,
    KeyUpdateRequest,
    SearchRequest,
)
from src.engine.llm.config import LlmConfig
from src.engine.rag import chunk_text, embed_query, embed_texts
from src.platform.authz import assert_owner_or_admin
from src.platform.llm_resource.repository import LlmResourceRepository
from src.platform.user.model import User

logger = logging.getLogger(__name__)

_EMBED_BATCH = 16
_DEFAULT_RAG_TYPE = "chatbot_shared"


class RagService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = RagRepository(session)

    # ── 임베딩 설정 해석 ──
    def _embedding_config(self) -> LlmConfig:
        resources = [
            r for r in LlmResourceRepository(self.session).list_by_type("embedding") if r.is_active
        ]
        if not resources:
            raise ValidationError(
                "활성 embedding 리소스가 없습니다. LLM 리소스에 embedding 타입을 추가하세요.",
            )
        r = sorted(resources, key=lambda x: x.priority, reverse=True)[0]
        model = r.deployment_name if r.provider == "azure" else (r.model_name or r.name)
        return LlmConfig(
            provider=r.provider,
            model=model or r.name,
            api_key=r.api_key or None,
            api_base=r.api_base or None,
            api_version=r.api_version or None,
        )

    # ── 그룹 ──
    def list_groups(self, user: User) -> list[tuple[RagGroupConfig, int, int]]:
        out: list[tuple[RagGroupConfig, int, int]] = []
        for g in self.repo.list_groups(user.id):
            out.append(
                (
                    g,
                    self.repo.count_keys_in_group(user.id, g.name),
                    self.repo.count_docs_in_group(g.name),
                )
            )
        return out

    def create_group(self, user: User, req: GroupCreateRequest) -> RagGroupConfig:
        g = RagGroupConfig(
            user_id=user.id,
            name=req.name,
            description=req.description,
            color=req.color or "#6366f1",
        )
        return self.repo.create_group(g)

    def update_group(self, user: User, group_id: str, req: GroupUpdateRequest) -> RagGroupConfig:
        g = self._owned_group(group_id, user)
        if req.name is not None:
            g.name = req.name
        if req.description is not None:
            g.description = req.description
        if req.color is not None:
            g.color = req.color
        return self.repo.save_group(g)

    def delete_group(self, user: User, group_id: str) -> None:
        g = self._owned_group(group_id, user)
        self.repo.delete_group(g)

    def group_counts(self, user: User, g: RagGroupConfig) -> tuple[int, int]:
        return self.repo.count_keys_in_group(user.id, g.name), self.repo.count_docs_in_group(g.name)

    # ── 키 ──
    def list_keys(self, user: User, rag_group: str | None = None) -> list[tuple[RagKeyConfig, int]]:
        return [
            (k, self.repo.count_docs_in_key(k.rag_key))
            for k in self.repo.list_keys(user.id, rag_group)
        ]

    def list_group_keys(self, user: User, group_id: str) -> list[tuple[RagKeyConfig, int]]:
        g = self._owned_group(group_id, user)
        return self.list_keys(user, rag_group=g.name)

    def create_key(self, user: User, req: KeyCreateRequest) -> RagKeyConfig:
        k = RagKeyConfig(
            user_id=user.id,
            rag_key=req.rag_key,
            rag_group=req.rag_group,
            description=req.description,
            rag_type=req.rag_type or _DEFAULT_RAG_TYPE,
        )
        return self.repo.create_key(k)

    def update_key(self, user: User, key_id: str, req: KeyUpdateRequest) -> RagKeyConfig:
        k = self._owned_key(key_id, user)
        if req.rag_group is not None:
            k.rag_group = req.rag_group
        if req.description is not None:
            k.description = req.description
        if req.rag_type is not None:
            k.rag_type = req.rag_type
        return self.repo.save_key(k)

    def delete_key(self, user: User, key_id: str, delete_docs: bool = False) -> None:
        k = self._owned_key(key_id, user)
        if delete_docs:
            for doc in self.repo.list_documents(rag_key=k.rag_key):
                self.repo.delete_document(doc)
        self.repo.delete_key(k)

    def key_doc_count(self, k: RagKeyConfig) -> int:
        return self.repo.count_docs_in_key(k.rag_key)

    # ── 문서 수집 ──
    def ingest_document(self, user: User, req: DocumentUploadRequest) -> tuple[Document, int]:
        rag_type = req.rag_type or _DEFAULT_RAG_TYPE
        cfg = self._embedding_config()  # 임베딩 리소스 없으면 400 (수집 전 검증)
        doc = self.repo.create_document(
            Document(
                user_id=user.id if rag_type == "user_isolated" else None,
                rag_key=req.rag_key,
                rag_group=req.rag_group,
                rag_type=rag_type,
                filename=req.filename,
                content=req.content,
            )
        )
        chunks = chunk_text(req.content)
        indexed = 0
        for i in range(0, len(chunks), _EMBED_BATCH):
            batch = chunks[i : i + _EMBED_BATCH]
            vectors = embed_texts(batch, cfg)
            indexed += self.repo.insert_embeddings(
                doc_id=doc.id,
                rag_key=req.rag_key,
                rag_group=req.rag_group,
                rag_type=rag_type,
                chunks=batch,
                vectors=vectors,
                start_index=i,
            )
        return doc, indexed

    def list_documents(
        self, user: User, rag_group: str | None, rag_key: str | None
    ) -> list[Document]:
        return self.repo.list_documents(rag_group=rag_group, rag_key=rag_key)

    def delete_document(self, user: User, doc_id: int) -> None:
        doc = self.repo.get_document(doc_id)
        if doc is None:
            raise NotFoundError("Document not found")
        self.repo.delete_document(doc)

    # ── 검색 ──
    def search(self, user: User, req: SearchRequest) -> list[dict]:
        cfg = self._embedding_config()
        qv = embed_query(req.query, cfg)
        return self.repo.vector_search_group(
            rag_group=req.rag_group, query_vector=qv, limit=req.limit
        )

    def rag_context(self, user: User, rag_group: str, query: str, *, limit: int = 3) -> str:
        """chat 사전 주입용 컨텍스트 (ADR-0012 §1). 검색된 상위 청크를 합친다.

        임베딩 미설정·검색 실패는 **빈 문자열**로 흘려보낸다(RAG는 선택적 — chat을 막지 않음).
        """
        try:
            cfg = self._embedding_config()
            qv = embed_query(query, cfg)
            results = self.repo.vector_search_group(
                rag_group=rag_group, query_vector=qv, limit=limit
            )
        except Exception:
            logger.exception("rag_context_retrieval_failed")
            return ""
        return "\n\n".join(r["content"] for r in results if r.get("content"))

    # ── 소유권 ──
    def _owned_group(self, group_id: str, user: User) -> RagGroupConfig:
        g = self.repo.get_group(group_id)
        if g is None:
            raise NotFoundError("RAG group not found")
        assert_owner_or_admin(user, g.user_id, message="Not your RAG group")
        return g

    def _owned_key(self, key_id: str, user: User) -> RagKeyConfig:
        k = self.repo.get_key(key_id)
        if k is None:
            raise NotFoundError("RAG key not found")
        assert_owner_or_admin(user, k.user_id, message="Not your RAG key")
        return k
