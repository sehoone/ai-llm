"""RAG 노드 — 지식베이스 시맨틱 검색 (ADR-0019 §2, ADR-0012).

engine은 `domains/rag`를 직접 import하지 않는다 — **ctx에 주입된 `rag_search` 포트**만 호출한다.
v3 rag는 그룹 기반이므로 `rag_group`(없으면 `rag_key` 폴백)으로 검색한다.

config: {"rag_group": "...", "query": "{{input.question}}", "limit": 5}
출력: {"results": [{content, similarity, ...}], "text": "<합친 청크 텍스트>"}
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.engine.workflow.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext

logger = logging.getLogger(__name__)


class RAGNode(BaseNode):
    node_type = "rag"

    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
        rag_group: str = (
            inputs.get("rag_group")
            or config.get("rag_group")
            or inputs.get("rag_key")
            or config.get("rag_key", "")
        )
        query: str = inputs.get("query") or config.get("query", "")
        limit: int = int(config.get("limit", 5))

        if not rag_group:
            raise ValueError("RAG node requires 'rag_group' (or legacy 'rag_key').")
        if not query:
            raise ValueError("RAG node requires 'query'.")
        if ctx.rag_search is None:
            raise ValueError("RAG search port not injected — rag node unavailable in this context.")

        results = await ctx.rag_search(query=query, rag_group=rag_group, limit=limit)
        combined_text = "\n\n".join(r.get("content", "") for r in results)

        logger.info("rag_node_executed rag_group=%s result_count=%d", rag_group, len(results))
        return {"results": results, "text": combined_text}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "rag_group": {"type": "string", "description": "Knowledge base group id"},
                "query": {"type": "string", "description": "Search query — supports templates"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["rag_group", "query"],
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "results": {"type": "array", "description": "Matching chunks"},
                "text": {"type": "string", "description": "Concatenated chunk text"},
            },
        }
