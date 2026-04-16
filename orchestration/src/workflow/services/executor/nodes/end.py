"""End node — workflow exit point.

Collects declared output variables from the execution context and returns them
as the workflow's final output.

Config schema:
    {
        "outputs": [
            {"name": "result", "value": "{{nodes.llm-1.output.text}}"},
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


class EndNode(BaseNode):
    node_type = "end"

    async def execute(self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext") -> dict[str, Any]:
        outputs_config: list[dict] = config.get("outputs", [])

        if not outputs_config:
            # No explicit mapping — pass through all inputs
            logger.info("end_node_executed", output_count=len(inputs))
            return inputs

        result: dict[str, Any] = {}
        for output_def in outputs_config:
            name = output_def["name"]
            # value is a template string resolved by the engine before calling execute,
            # so by the time we reach here it's already in `inputs`
            result[name] = inputs.get(name)

        logger.info("end_node_executed", output_count=len(result))
        return result

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "outputs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "string", "description": "Template expression, e.g. {{nodes.llm-1.output.text}}"},
                        },
                        "required": ["name", "value"],
                    },
                }
            },
        }
