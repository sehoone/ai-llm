"""RAG node — semantic search over an existing knowledge base.

Config schema:
    {
        "rag_key":  "my-bot",          # knowledge base identifier
        "rag_type": "chatbot_shared",  # "chatbot_shared" | "user_isolated"
        "query":    "{{input.question}}",
        "limit":    5
    }

Output:
    {
        "results": [{"content": "...", "similarity": 0.9, "filename": "..."}, ...],
        "text":    "<concatenated chunk text>"
    }
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.common.logging import logger
from src.workflow.services.executor.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.workflow.services.executor.context import ExecutionContext


class RAGNode(BaseNode):
    node_type = "rag"

    async def execute(self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext") -> dict[str, Any]:
        # Late import to avoid circular deps
        from src.rag.services.rag_service import rag_service

        rag_key: str = inputs.get("rag_key") or config.get("rag_key", "")
        rag_type: str = inputs.get("rag_type") or config.get("rag_type", "chatbot_shared")
        query: str = inputs.get("query") or config.get("query", "")
        limit: int = int(config.get("limit", 5))

        if not rag_key:
            raise ValueError("RAG node requires 'rag_key'.")
        if not query:
            raise ValueError("RAG node requires 'query'.")

        # user_id is None for shared RAGs
        user_id = None
        if rag_type == "user_isolated":
            # Inject user_id via execution context if available
            user_id = getattr(ctx, "user_id", None)

        results: list[dict] = await rag_service.search_rag(
            rag_key=rag_key,
            rag_type=rag_type,
            user_id=user_id,
            query=query,
            limit=limit,
        )

        # Serialise result rows (they come back as Row objects from SQLAlchemy)
        serialised = []
        for row in results:
            if hasattr(row, "_asdict"):
                d = row._asdict()
            elif hasattr(row, "__dict__"):
                d = {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
            else:
                d = dict(row)
            # similarity may be a Decimal — convert to float
            if "similarity" in d:
                d["similarity"] = float(d["similarity"])
            serialised.append(d)

        combined_text = "\n\n".join(r.get("content", "") for r in serialised)
        logger.info("rag_node_executed", rag_key=rag_key, result_count=len(serialised))

        return {"results": serialised, "text": combined_text}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "rag_key":  {"type": "string", "description": "Knowledge base identifier"},
                "rag_type": {"type": "string", "enum": ["chatbot_shared", "user_isolated", "natural_search"]},
                "query":    {"type": "string", "description": "Search query — supports template expressions"},
                "limit":    {"type": "integer", "default": 5},
            },
            "required": ["rag_key", "query"],
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "results": {"type": "array", "description": "Array of matching chunks"},
                "text":    {"type": "string", "description": "Concatenated chunk text"},
            },
        }
