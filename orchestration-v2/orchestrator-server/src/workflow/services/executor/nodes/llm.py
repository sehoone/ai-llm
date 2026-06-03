"""LLM node — calls an LLM with a prompt template.

Config schema:
    {
        "model": "gpt-4o-mini",          # optional, defaults to settings.DEFAULT_LLM_MODEL
        "system_prompt": "You are ...",  # optional
        "prompt": "User said: {{input.user_message}}"
    }

Output:
    {"text": "<assistant reply>"}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.common.logging import logger
from src.common.services.llm import LLMService
from src.workflow.services.executor.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.workflow.services.executor.context import ExecutionContext


class LLMNode(BaseNode):
    node_type = "llm"

    async def execute(self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext") -> dict[str, Any]:
        prompt: str = inputs.get("prompt") or config.get("prompt", "")
        system_prompt: str = config.get("system_prompt", "")
        model_name: str | None = config.get("model") or None

        if not prompt:
            raise ValueError("LLM node requires a 'prompt' value.")

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        # Each node gets its own LLMService instance to avoid shared state issues
        service = LLMService()
        response = await service.call(messages, model_name=model_name)

        text = response.content if hasattr(response, "content") else str(response)
        logger.info("llm_node_executed", model=model_name, prompt_length=len(prompt), response_length=len(text))

        return {"text": text}

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "LLM model name. Defaults to system default.",
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
            "properties": {
                "text": {"type": "string", "description": "LLM response text"},
            },
        }
