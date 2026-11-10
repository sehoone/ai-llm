"""Condition 노드 — boolean 식을 평가해 true/false 분기로 라우팅 (V2 계승).

config: {"left": "{{nodes.llm-1.output.text}}", "operator": "contains", "right": "yes"}
출력 {"result": bool} — 러너가 `result`를 읽어 따라갈 엣지 handle("true"|"false")을 결정한다.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.engine.workflow.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext

logger = logging.getLogger(__name__)

OPERATORS = {
    "contains": lambda a, b: str(b).lower() in str(a).lower(),
    "not_contains": lambda a, b: str(b).lower() not in str(a).lower(),
    "equals": lambda a, b: str(a) == str(b),
    "not_equals": lambda a, b: str(a) != str(b),
    "starts_with": lambda a, b: str(a).lower().startswith(str(b).lower()),
    "ends_with": lambda a, b: str(a).lower().endswith(str(b).lower()),
    "not_empty": lambda a, b: bool(str(a).strip()),
    "is_empty": lambda a, b: not bool(str(a).strip()),
    "greater_than": lambda a, b: float(a) > float(b),
    "less_than": lambda a, b: float(a) < float(b),
    "greater_than_or_equal": lambda a, b: float(a) >= float(b),
    "less_than_or_equal": lambda a, b: float(a) <= float(b),
}


class ConditionNode(BaseNode):
    node_type = "condition"

    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
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

        logger.info("condition_node_executed operator=%s result=%s", operator, result)
        return {"result": result}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "left": {"type": "string", "description": "Left operand — template or literal."},
                "operator": {"type": "string", "enum": list(OPERATORS)},
                "right": {"type": "string", "description": "Right operand (unused for unary operators)."},
            },
            "required": ["left", "operator"],
        }

    def output_schema(self) -> dict:
        return {"type": "object", "properties": {"result": {"type": "boolean"}}}
