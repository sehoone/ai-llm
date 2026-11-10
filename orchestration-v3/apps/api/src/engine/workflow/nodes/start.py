"""Start 노드 — 워크플로우 진입점. input_data 검증·통과 (V2 계승).

config: {"variables": [{"name": "...", "type": "string", "required": true, "default": ...}, ...]}
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.engine.workflow.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext

logger = logging.getLogger(__name__)


class StartNode(BaseNode):
    node_type = "start"

    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
        variables: list[dict] = config.get("variables", [])

        for var in variables:
            if var.get("required") and var["name"] not in ctx.input_data:
                raise ValueError(f"Required input variable '{var['name']}' is missing.")

        output: dict[str, Any] = {}
        for var in variables:
            name = var["name"]
            if name in ctx.input_data:
                output[name] = ctx.input_data[name]
            elif "default" in var:
                output[name] = var["default"]

        logger.info("start_node_executed variable_count=%d", len(variables))
        return output

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "variables": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string", "enum": ["string", "number", "boolean", "object"]},
                            "required": {"type": "boolean"},
                            "description": {"type": "string"},
                            "default": {},
                        },
                        "required": ["name", "type"],
                    },
                }
            },
        }
