"""HTTP 노드 — 외부 REST API 호출 (V2 계승). 모든 필드는 실행 전 템플릿 해석된다.

config: {"url", "method", "headers", "body", "timeout"}
출력: {"status_code", "body", "headers", "json"}
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import httpx

from src.engine.workflow.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext

logger = logging.getLogger(__name__)

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class HTTPNode(BaseNode):
    node_type = "http"

    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
        url: str = inputs.get("url") or config.get("url", "")
        method: str = (inputs.get("method") or config.get("method", "GET")).upper()
        headers: dict = inputs.get("headers") or config.get("headers") or {}
        body: Any = inputs.get("body") or config.get("body")
        timeout: float = float(config.get("timeout", 30))

        if not url:
            raise ValueError("HTTP node requires 'url'.")
        if method not in _ALLOWED_METHODS:
            raise ValueError(f"Unsupported HTTP method '{method}'. Allowed: {_ALLOWED_METHODS}")

        request_content: bytes | None = None
        request_json: Any = None
        if body:
            if isinstance(body, (dict, list)):
                request_json = body
            else:
                try:
                    request_json = json.loads(body)
                except (json.JSONDecodeError, TypeError):
                    request_content = str(body).encode()

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.request(
                method=method, url=url, headers=headers, content=request_content, json=request_json
            )

        parsed_json = None
        try:
            parsed_json = response.json()
        except Exception:  # noqa: BLE001 — 비 JSON 응답은 정상 경로
            pass

        logger.info("http_node_executed method=%s url=%s status=%d", method, url, response.status_code)
        return {
            "status_code": response.status_code,
            "body": response.text,
            "headers": dict(response.headers),
            "json": parsed_json,
        }

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Request URL — supports templates"},
                "method": {"type": "string", "enum": sorted(_ALLOWED_METHODS), "default": "GET"},
                "headers": {"type": "object", "description": "HTTP headers (key-value)"},
                "body": {"type": "string", "description": "Request body — string or JSON"},
                "timeout": {"type": "number", "default": 30},
            },
            "required": ["url"],
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status_code": {"type": "integer"},
                "body": {"type": "string"},
                "headers": {"type": "object"},
                "json": {"description": "Parsed JSON body if applicable"},
            },
        }
