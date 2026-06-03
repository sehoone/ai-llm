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
        # `inputs` is the already-resolved version of the node config.
        # Each entry in outputs has its `value` template already substituted.
        outputs_config: list[dict] = inputs.get("outputs", [])

        if not outputs_config:
            # No explicit mapping — pass through all inputs
            logger.info("end_node_executed", output_count=len(inputs))
            return inputs

        result: dict[str, Any] = {}
        for output_def in outputs_config:
            name = output_def.get("name")
            value = output_def.get("value")
            if name:
                result[name] = value

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
