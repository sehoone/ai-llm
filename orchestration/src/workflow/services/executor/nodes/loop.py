"""Loop node — iterates over an array and processes each item.

Config fields:
    items_path   : template expression that resolves to a list (e.g. "{{nodes.rag-1.output.results}}")
    item_var     : name to bind the current item inside processor templates (default: "item")
    processor    : "passthrough" | "llm" | "http"
    -- llm processor --
    model        : model id (default "gpt-4o-mini")
    prompt       : template; can reference {{item}} or {{item.<field>}}
    -- http processor --
    url          : URL template
    method       : GET | POST | PUT | PATCH | DELETE
    body         : request body template (JSON string)

Output:
    results      : list of processed outputs (one per input item)
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import httpx

from src.common.logging import logger
from src.workflow.services.executor.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.workflow.services.executor.context import ExecutionContext

_TEMPLATE_RE = re.compile(r"\{\{\s*([\w.\[\]\-]+)\s*\}\}")


def _resolve(template: str, item: Any, item_var: str) -> str:
    """Replace {{item}} / {{item.<key>}} with actual values."""
    def _replace(m: re.Match) -> str:
        path = m.group(1)
        parts = path.split(".")
        if parts[0] != item_var:
            return m.group(0)  # leave other templates untouched
        val = item
        for part in parts[1:]:
            if isinstance(val, dict):
                val = val.get(part, "")
            else:
                val = ""
        return str(val) if val is not None else ""

    return _TEMPLATE_RE.sub(_replace, template)


class LoopNode(BaseNode):
    node_type = "loop"

    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
        items_raw = inputs.get("items", [])
        if isinstance(items_raw, str):
            try:
                items_raw = json.loads(items_raw)
            except json.JSONDecodeError:
                items_raw = [items_raw]
        if not isinstance(items_raw, list):
            items_raw = [items_raw]

        item_var: str = config.get("item_var", "item") or "item"
        processor: str = config.get("processor", "passthrough")

        results: list[Any] = []

        for item in items_raw:
            if processor == "llm":
                out = await self._process_llm(item, item_var, config, ctx)
            elif processor == "http":
                out = await self._process_http(item, item_var, config)
            else:
                out = item

            results.append(out)

        logger.info("loop_node_completed", items=len(items_raw), processor=processor)
        return {"results": results, "count": len(results)}

    # ── processors ──────────────────────────────────────────────────────────

    async def _process_llm(
        self, item: Any, item_var: str, config: dict, ctx: "ExecutionContext"
    ) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage
        from src.common.services.llm import LLMService

        model: str = config.get("model", "gpt-4o-mini") or "gpt-4o-mini"
        prompt_tpl: str = config.get("prompt", "") or ""
        system_tpl: str = config.get("system_prompt", "") or ""

        prompt = _resolve(prompt_tpl, item, item_var)
        system = _resolve(system_tpl, item, item_var)

        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        service = LLMService(model=model)
        response = await service.call(messages)
        return response.content if hasattr(response, "content") else str(response)

    async def _process_http(
        self, item: Any, item_var: str, config: dict
    ) -> dict:
        url_tpl: str = config.get("url", "") or ""
        method: str = (config.get("method", "GET") or "GET").upper()
        body_tpl: str = config.get("body", "") or ""
        timeout: int = int(config.get("timeout", 30) or 30)

        url = _resolve(url_tpl, item, item_var)
        body_str = _resolve(body_tpl, item, item_var)

        body: Any = None
        if body_str:
            try:
                body = json.loads(body_str)
            except json.JSONDecodeError:
                body = body_str

        async with httpx.AsyncClient(timeout=timeout) as client:
            req_kwargs: dict = {"url": url}
            if body is not None:
                req_kwargs["json" if isinstance(body, dict) else "content"] = body

            resp = await client.request(method, **req_kwargs)

        try:
            resp_json = resp.json()
        except Exception:
            resp_json = None

        return {
            "status_code": resp.status_code,
            "body": resp.text,
            "json": resp_json,
        }

    def input_schema(self) -> dict:
        return {
            "items": {"type": "string", "description": "Template resolving to an array"},
            "item_var": {"type": "string", "description": "Variable name for current item"},
            "processor": {"type": "string", "enum": ["passthrough", "llm", "http"]},
            "model": {"type": "string"},
            "prompt": {"type": "string"},
            "system_prompt": {"type": "string"},
            "url": {"type": "string"},
            "method": {"type": "string"},
            "body": {"type": "string"},
            "timeout": {"type": "number"},
        }

    def output_schema(self) -> dict:
        return {
            "results": {"type": "array", "description": "Processed outputs list"},
            "count": {"type": "number", "description": "Number of items processed"},
        }
