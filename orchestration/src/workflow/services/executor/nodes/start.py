"""Start node — workflow entry point.

Validates and passes through the workflow's input_data.
Config schema:
    {
        "variables": [
            {"name": "user_input", "type": "string", "required": true, "description": "..."},
            ...
        ]
    }
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.common.logging import logger
from src.workflow.services.executor.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.workflow.services.executor.context import ExecutionContext


class StartNode(BaseNode):
    node_type = "start"

    async def execute(self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext") -> dict[str, Any]:
        variables: list[dict] = config.get("variables", [])

        # Validate required variables
        for var in variables:
            if var.get("required") and var["name"] not in ctx.input_data:
                raise ValueError(f"Required input variable '{var['name']}' is missing.")

        # Output all declared variables (falling back to defaults if provided)
        output: dict[str, Any] = {}
        for var in variables:
            name = var["name"]
            if name in ctx.input_data:
                output[name] = ctx.input_data[name]
            elif "default" in var:
                output[name] = var["default"]

        logger.info("start_node_executed", variable_count=len(variables))
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
