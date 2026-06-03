"""HTTP node — call an external REST API.

Config schema:
    {
        "url":     "https://api.example.com/{{input.resource}}",
        "method":  "GET",          # GET | POST | PUT | PATCH | DELETE
        "headers": {"Authorization": "Bearer {{input.token}}"},
        "body":    "{{input.payload}}",   # string or JSON string
        "timeout": 30
    }

All fields are template-resolved before execution.

Output:
    {
        "status_code": 200,
        "body":        "...",
        "headers":     {"Content-Type": "application/json"},
        "json":        {...}     # if response is valid JSON, else null
    }
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from src.common.logging import logger
from src.workflow.services.executor.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.workflow.services.executor.context import ExecutionContext

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class HTTPNode(BaseNode):
    node_type = "http"

    async def execute(self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext") -> dict[str, Any]:
        url: str = inputs.get("url") or config.get("url", "")
        method: str = (inputs.get("method") or config.get("method", "GET")).upper()
        headers: dict = inputs.get("headers") or config.get("headers") or {}
        body: Any = inputs.get("body") or config.get("body")
        timeout: float = float(config.get("timeout", 30))

        if not url:
            raise ValueError("HTTP node requires 'url'.")
        if method not in _ALLOWED_METHODS:
            raise ValueError(f"Unsupported HTTP method '{method}'. Allowed: {_ALLOWED_METHODS}")

        # Normalise body
        request_content: bytes | None = None
        request_json: Any = None
        if body:
            if isinstance(body, (dict, list)):
                request_json = body
            else:
                # Try to parse as JSON; fall back to raw string
                try:
                    request_json = json.loads(body)
                except (json.JSONDecodeError, TypeError):
                    request_content = str(body).encode()

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=request_content,
                json=request_json,
            )

        body_text = response.text
        parsed_json = None
        try:
            parsed_json = response.json()
        except Exception:
            pass

        logger.info(
            "http_node_executed",
            method=method,
            url=url,
            status_code=response.status_code,
        )

        return {
            "status_code": response.status_code,
            "body": body_text,
            "headers": dict(response.headers),
            "json": parsed_json,
        }

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url":     {"type": "string", "description": "Request URL — supports templates"},
                "method":  {"type": "string", "enum": list(_ALLOWED_METHODS), "default": "GET"},
                "headers": {"type": "object", "description": "HTTP headers (key-value pairs)"},
                "body":    {"type": "string", "description": "Request body — string or JSON"},
                "timeout": {"type": "number", "default": 30},
            },
            "required": ["url"],
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status_code": {"type": "integer"},
                "body":        {"type": "string"},
                "headers":     {"type": "object"},
                "json":        {"description": "Parsed JSON body if applicable"},
            },
        }
