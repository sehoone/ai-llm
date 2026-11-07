"""rag: 청킹·임베딩 (순수) — ADR-0005 / ADR-0012 §2.

engine은 DB를 모른다. 벡터 저장·검색(pgvector SQL)은 domains/rag가 소유한다. 여기서는 텍스트
청킹과 LiteLLM 임베딩 호출만 제공한다(설정은 `LlmConfig`로 주입).
"""

from __future__ import annotations

from collections.abc import Sequence

import litellm

from src.engine.llm.config import LlmConfig

_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 100


def chunk_text(text: str, *, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """문자 기반 오버랩 청킹 (V2 계승). 항상 전진 보장."""
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        new_start = end - overlap
        start = new_start if new_start > start else start + max(1, size - overlap)
    return chunks


def embed_texts(texts: Sequence[str], config: LlmConfig) -> list[list[float]]:
    """LiteLLM로 여러 텍스트를 임베딩. provider 중립(ADR-0012 §2)."""
    params = {"model": config.model_id, "input": list(texts)}
    if config.api_key:
        params["api_key"] = config.api_key
    if config.api_base:
        params["api_base"] = config.api_base
    if config.api_version:
        params["api_version"] = config.api_version
    resp = litellm.embedding(**params)
    return [item["embedding"] for item in resp.data]


def embed_query(text: str, config: LlmConfig) -> list[float]:
    """단일 쿼리 임베딩."""
    return embed_texts([text], config)[0]


__all__ = ["chunk_text", "embed_texts", "embed_query"]
