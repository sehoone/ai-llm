"""End 노드 — 워크플로우 종료점. 선언된 출력 변수를 모아 최종 output으로 반환 (V2 계승).

config: {"outputs": [{"name": "result", "value": "{{nodes.llm-1.output.text}}"}, ...]}
`outputs`가 없으면 해석된 inputs 전체를 통과시킨다.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.engine.workflow.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext

logger = logging.getLogger(__name__)


class EndNode(BaseNode):
    node_type = "end"

    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
        # `inputs`는 config를 해석한 버전 — 각 outputs.value 템플릿이 이미 치환돼 있다.
        outputs_config: list[dict] = inputs.get("outputs", [])

        if not outputs_config:
            logger.info("end_node_executed output_count=%d", len(inputs))
            return inputs

        result: dict[str, Any] = {}
        for output_def in outputs_config:
            name = output_def.get("name")
            if name:
                result[name] = output_def.get("value")

        logger.info("end_node_executed output_count=%d", len(result))
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
                            "value": {
                                "type": "string",
                                "description": "Template expression, e.g. {{nodes.llm-1.output.text}}",
                            },
                        },
                        "required": ["name", "value"],
                    },
                }
            },
        }
