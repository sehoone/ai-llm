"""도메인이 주입하는 포트 (ADR-0019 §2).

engine은 외부 의존(rag 검색·LLM 설정)을 직접 import하지 않는다(ADR-0005 단방향 경계). 대신 도메인이
구현을 `ExecutionContext`에 콜백/값으로 주입하고, 노드는 주입된 것만 호출한다.

- `RagSearch`: pgvector 검색은 `domains/rag`(DB) 소유 → 콜백으로 주입.
- `llm_config`: 모델 선택은 `llm_resource` 테이블(DB) → 도메인이 `LlmConfig`로 해석해 값 주입(ADR-0010).
"""

from __future__ import annotations

from typing import Any, Protocol


class RagSearch(Protocol):
    """지식베이스 검색 포트. 도메인이 `domains/rag` 호출 구현을 주입한다."""

    async def __call__(self, *, query: str, rag_group: str, limit: int) -> list[dict[str, Any]]: ...
