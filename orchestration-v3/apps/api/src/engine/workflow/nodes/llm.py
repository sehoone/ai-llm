"""LLM 노드 — 프롬프트 템플릿으로 LLM 호출 (ADR-0019 §2, ADR-0010).

V2의 `LLMService` 대신 **ctx에 주입된 `LlmConfig`로 `engine.llm.build_chat_model(cfg)`**를 조립해
`.invoke()`한다(모델 선택은 도메인이 `llm_resource`에서 해석 — engine은 DB/env 미참조).

config: {"system_prompt": "...", "prompt": "User said: {{input.user_message}}"}
출력: {"text": "<assistant reply>"}
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage

from src.engine.llm import build_chat_model
from src.engine.workflow.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext

logger = logging.getLogger(__name__)


def _as_int(value: Any) -> int | None:
    """llm_resource_id 정규화 — 숫자/숫자문자열은 int, 그 외(빈 값 포함)는 None."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class LLMNode(BaseNode):
    node_type = "llm"

    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
        prompt: str = inputs.get("prompt") or config.get("prompt", "")
        system_prompt: str = inputs.get("system_prompt") or config.get("system_prompt", "")
        resource_id = config.get("llm_resource_id")

        if not prompt:
            raise ValueError("LLM node requires a 'prompt' value.")

        cfg = ctx.llm_config_for(_as_int(resource_id))
        if cfg is None:
            raise ValueError(
                "No active chat LLM resource — register an llm_resource (resource_type=chat) "
                "or select one on the node."
            )

        model = build_chat_model(cfg, system_prompt=system_prompt or None)
        # 동기 invoke를 스레드로 — 이벤트 루프 블로킹 회피.
        result = await asyncio.to_thread(model.invoke, [HumanMessage(content=prompt)])
        text = result.content if hasattr(result, "content") else str(result)

        logger.info("llm_node_executed prompt_length=%d response_length=%d", len(prompt), len(text))
        return {"text": text}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "llm_resource_id": {
                    "type": "integer",
                    "description": "사용할 llm_resource(chat) id. 미지정 시 기본 chat 리소스.",
                },
                "system_prompt": {"type": "string"},
                "prompt": {
                    "type": "string",
                    "description": "Prompt template. Use {{variables}} for interpolation.",
                },
            },
            "required": ["prompt"],
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "LLM response text"}},
        }
