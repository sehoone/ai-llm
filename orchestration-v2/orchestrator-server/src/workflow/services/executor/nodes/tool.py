"""Tool node — invoke a registered built-in tool.

Config schema:
    {
        "tool":  "web_search",
        "query": "{{input.search_term}}"
    }

Supported tools:
    web_search — DuckDuckGo search (reuses existing langchain tool)

Output:
    {"results": "<raw tool output string>"}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.common.logging import logger
from src.workflow.services.executor.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.workflow.services.executor.context import ExecutionContext

_SUPPORTED_TOOLS = ("web_search",)


class ToolNode(BaseNode):
    node_type = "tool"

    async def execute(self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext") -> dict[str, Any]:
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
        import asyncio
        from langchain_community.tools import DuckDuckGoSearchResults

        tool = DuckDuckGoSearchResults(num_results=8, handle_tool_error=True)

        # LangChain tools are sync — run in thread pool
        raw: str = await asyncio.to_thread(tool.run, query)
        logger.info("tool_node_web_search_executed", query=query, result_length=len(raw))
        return {"results": raw}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tool":  {"type": "string", "enum": list(_SUPPORTED_TOOLS), "default": "web_search"},
                "query": {"type": "string", "description": "Search query — supports template expressions"},
            },
            "required": ["query"],
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "results": {"type": "string", "description": "Raw tool output text"},
            },
        }
