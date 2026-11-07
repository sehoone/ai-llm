"""ChatLiteLLM 기반 모델 어댑터 (ADR-0010 §1·§4).

`LlmChatModel`은 그래프의 `ChatModel` 프로토콜(ADR-0008)을 만족하는 **동기 invoke** 어댑터로,
시스템 프롬프트가 없으면 선주입한다. `build_chat_model`은 주입된 `LlmConfig`만으로 모델을 조립한다
(순수 — DB 미의존).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_litellm import ChatLiteLLM

from src.engine.llm.config import LlmConfig


class LlmChatModel:
    """그래프 모델 노드용 동기 어댑터. 내부 LangChain Runnable을 감싼다."""

    def __init__(self, runnable: Any, *, system_prompt: str | None = None) -> None:
        self._runnable = runnable
        self._system_prompt = system_prompt

    def invoke(self, messages: list[BaseMessage], config: Any = None) -> AIMessage:
        msgs = list(messages)
        if self._system_prompt and not any(isinstance(m, SystemMessage) for m in msgs):
            msgs = [SystemMessage(content=self._system_prompt), *msgs]
        # config 포워딩 → LangGraph stream_mode="messages" 토큰 콜백 전파 (ADR-0011 §2).
        result = self._runnable.invoke(msgs, config=config) if config is not None else self._runnable.invoke(msgs)
        if isinstance(result, AIMessage):
            return result
        # chat model은 AIMessage를 반환하지만 방어적으로 변환.
        return AIMessage(content=getattr(result, "content", str(result)))


def build_chat_model(
    config: LlmConfig,
    *,
    tools: Sequence[Any] | None = None,
    system_prompt: str | None = None,
) -> LlmChatModel:
    """`LlmConfig`로 ChatLiteLLM을 조립해 `LlmChatModel`로 감싼다.

    `tools`가 있으면 bind_tools(Phase 2+ 실도구용 — Phase 0 chat 기본 경로는 비움).
    """
    # streaming=True → .invoke()도 토큰 콜백을 발생시켜 messages 모드가 조각을 포착 (ADR-0011 §2).
    params: dict[str, Any] = {"model": config.model_id, "streaming": True}
    if config.api_key:
        params["api_key"] = config.api_key
    if config.api_base:
        params["api_base"] = config.api_base
    if config.api_version:
        params["api_version"] = config.api_version
    if config.max_tokens:
        params["max_tokens"] = config.max_tokens
    if not config.is_reasoning and config.temperature is not None:
        params["temperature"] = config.temperature

    llm: Any = ChatLiteLLM(**params)
    if tools:
        llm = llm.bind_tools(list(tools))
    return LlmChatModel(llm, system_prompt=system_prompt)
