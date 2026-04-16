"""Condition node — evaluates a boolean expression and routes to true/false branch.

Config schema:
    {
        "left":      "{{nodes.llm-1.output.text}}",
        "operator":  "contains",   # see OPERATORS below
        "right":     "yes"         # comparand (optional for unary operators)
    }

Supported operators:
    contains, not_contains, equals, not_equals,
    starts_with, ends_with, not_empty, is_empty,
    greater_than, less_than, greater_than_or_equal, less_than_or_equal

Output:
    {"result": true | false}

The engine reads `result` to decide which outgoing edge handle to follow
("true" or "false").
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.common.logging import logger
from src.workflow.services.executor.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.workflow.services.executor.context import ExecutionContext

OPERATORS = {
    "contains":                 lambda l, r: str(r).lower() in str(l).lower(),
    "not_contains":             lambda l, r: str(r).lower() not in str(l).lower(),
    "equals":                   lambda l, r: str(l) == str(r),
    "not_equals":               lambda l, r: str(l) != str(r),
    "starts_with":              lambda l, r: str(l).lower().startswith(str(r).lower()),
    "ends_with":                lambda l, r: str(l).lower().endswith(str(r).lower()),
    "not_empty":                lambda l, r: bool(str(l).strip()),
    "is_empty":                 lambda l, r: not bool(str(l).strip()),
    "greater_than":             lambda l, r: float(l) > float(r),
    "less_than":                lambda l, r: float(l) < float(r),
    "greater_than_or_equal":    lambda l, r: float(l) >= float(r),
    "less_than_or_equal":       lambda l, r: float(l) <= float(r),
}


class ConditionNode(BaseNode):
    node_type = "condition"

    async def execute(self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext") -> dict[str, Any]:
        left = inputs.get("left", config.get("left", ""))
        operator: str = config.get("operator", "not_empty")
        right = inputs.get("right", config.get("right", ""))

        evaluator = OPERATORS.get(operator)
        if evaluator is None:
            raise ValueError(f"Unknown condition operator '{operator}'. Valid: {list(OPERATORS)}")

        try:
            result: bool = bool(evaluator(left, right))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Condition evaluation failed ({operator}): {exc}") from exc

        logger.info("condition_node_executed", operator=operator, result=result)
        return {"result": result}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "left": {
                    "type": "string",
                    "description": "Left operand — template expression or literal.",
                },
                "operator": {
                    "type": "string",
                    "enum": list(OPERATORS),
                },
                "right": {
                    "type": "string",
                    "description": "Right operand (not needed for unary operators like not_empty).",
                },
            },
            "required": ["left", "operator"],
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "result": {"type": "boolean"},
            },
        }
