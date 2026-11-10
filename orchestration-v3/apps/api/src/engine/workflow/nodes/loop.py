"""Loop 노드 — 배열을 순회하며 각 항목을 처리 (ADR-0019, V2 계승).

config:
    items (또는 inputs.items) : 배열로 해석되는 템플릿
    item_var                  : 항목 바인딩 이름(기본 "item")
    processor                 : "passthrough" | "llm" | "http"
    (llm) system_prompt·prompt : {{item}}·{{item.<field>}} 참조 가능 — 모델은 주입된 llm_config 사용
    (http) url·method·body     : {{item}} 참조 가능

출력: {"results": [...], "count": n}
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from src.engine.llm import build_chat_model
from src.engine.workflow.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext

logger = logging.getLogger(__name__)

_TEMPLATE_RE = re.compile(r"\{\{\s*([\w.\[\]\-]+)\s*\}\}")


def _resolve(template: str, item: Any, item_var: str) -> str:
    """{{item}} / {{item.<key>}}를 실제 값으로 치환. 다른 템플릿은 그대로 둔다."""

    def _replace(m: re.Match) -> str:
        parts = m.group(1).split(".")
        if parts[0] != item_var:
            return m.group(0)
        val = item
        for part in parts[1:]:
            val = val.get(part, "") if isinstance(val, dict) else ""
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
                results.append(await self._process_llm(item, item_var, config, ctx))
            elif processor == "http":
                results.append(await self._process_http(item, item_var, config))
            else:
                results.append(item)

        logger.info("loop_node_completed items=%d processor=%s", len(items_raw), processor)
        return {"results": results, "count": len(results)}

    async def _process_llm(
        self, item: Any, item_var: str, config: dict, ctx: "ExecutionContext"
    ) -> str:
        rid = config.get("llm_resource_id")
        cfg = ctx.llm_config_for(int(rid) if str(rid).isdigit() else None)
        if cfg is None:
            raise ValueError("Loop llm processor requires an active chat llm_resource.")
        prompt = _resolve(config.get("prompt", "") or "", item, item_var)
        system = _resolve(config.get("system_prompt", "") or "", item, item_var)

        messages: list[Any] = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        model = build_chat_model(cfg)
        result = await asyncio.to_thread(model.invoke, messages)
        return result.content if hasattr(result, "content") else str(result)

    async def _process_http(self, item: Any, item_var: str, config: dict) -> dict:
        url = _resolve(config.get("url", "") or "", item, item_var)
        method: str = (config.get("method", "GET") or "GET").upper()
        body_str = _resolve(config.get("body", "") or "", item, item_var)
        timeout: int = int(config.get("timeout", 30) or 30)

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
        except Exception:  # noqa: BLE001
            resp_json = None
        return {"status_code": resp.status_code, "body": resp.text, "json": resp_json}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "items": {"type": "string", "description": "Template resolving to an array"},
                "item_var": {"type": "string", "description": "Variable name for current item"},
                "processor": {"type": "string", "enum": ["passthrough", "llm", "http"]},
                "system_prompt": {"type": "string"},
                "prompt": {"type": "string"},
                "url": {"type": "string"},
                "method": {"type": "string"},
                "body": {"type": "string"},
                "timeout": {"type": "number"},
            },
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "results": {"type": "array", "description": "Processed outputs"},
                "count": {"type": "number"},
            },
        }
