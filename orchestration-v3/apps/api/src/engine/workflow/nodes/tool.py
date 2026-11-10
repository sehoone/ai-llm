"""Tool 노드 — 내장 도구 호출 (V2 계승). 현재 web_search(DuckDuckGo)만.

config: {"tool": "web_search", "query": "{{input.search_term}}"}
출력: {"results": "<raw tool output>"}

web_search는 `langchain-community` + `ddgs` 의존 — 미설치 시 실행 시점에 명확한 에러.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from src.engine.workflow.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext

logger = logging.getLogger(__name__)

_SUPPORTED_TOOLS = ("web_search",)


class ToolNode(BaseNode):
    node_type = "tool"

    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
        tool_name: str = config.get("tool", "web_search")
        query: str = inputs.get("query") or config.get("query", "")

        if not query:
            raise ValueError("Tool node requires 'query'.")
        if tool_name not in _SUPPORTED_TOOLS:
            raise ValueError(f"Unknown tool '{tool_name}'. Supported: {_SUPPORTED_TOOLS}")

        if tool_name == "web_search":
            return await self._web_search(query)
        raise RuntimeError(f"Tool '{tool_name}' is registered but has no handler.")

    @staticmethod
    async def _web_search(query: str) -> dict[str, Any]:
        try:
            from langchain_community.tools import DuckDuckGoSearchResults
        except ImportError as exc:
            raise RuntimeError(
                "web_search requires 'langchain-community' and 'ddgs'. Install them to use the tool node."
            ) from exc

        tool = DuckDuckGoSearchResults(num_results=8, handle_tool_error=True)
        # LangChain 도구는 동기 → 스레드풀에서 실행
        raw: str = await asyncio.to_thread(tool.run, query)
        logger.info("tool_node_web_search_executed query=%s result_length=%d", query, len(raw))
        return {"results": raw}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tool": {"type": "string", "enum": list(_SUPPORTED_TOOLS), "default": "web_search"},
                "query": {"type": "string", "description": "Search query — supports templates"},
            },
            "required": ["query"],
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"results": {"type": "string", "description": "Raw tool output text"}},
        }
