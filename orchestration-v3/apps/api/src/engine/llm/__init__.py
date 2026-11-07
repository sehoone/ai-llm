"""llm: 모델 호출 추상화 (provider·chat·stream). 프로바이더 중립 — ADR-0005 / ADR-0010.

- `LlmConfig`: 순수 설정 값.
- `build_chat_model(config)`: 값만으로 모델 조립.
- `default_llm_config()` / `build_default_chat_model()`: `core.config`(env) 기본값으로 조립
  (키 없으면 None — 호출측이 FakeToolCallingModel로 폴백, ADR-0010 §3).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.core.config import settings
from src.engine.llm.config import LlmConfig
from src.engine.llm.model import LlmChatModel, build_chat_model
from src.engine.llm.summary import generate_title
from src.engine.prompts import load_system_prompt


def default_llm_config() -> LlmConfig | None:
    """`core.config`(env)에서 기본 LLM 설정을 만든다. 미구성이면 None (ADR-0010 §3)."""
    if not settings.llm_is_configured:
        return None
    return LlmConfig(
        provider=settings.llm_provider,
        model=settings.llm_model,
        api_key=settings.llm_api_key or None,
        api_base=settings.llm_api_base or None,
        api_version=settings.llm_api_version or None,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens or None,
    )


def build_default_chat_model(
    *,
    tools: Sequence[Any] | None = None,
    system_prompt: str | None = None,
) -> LlmChatModel | None:
    """기본 설정으로 챗 모델을 조립. 미구성이면 None."""
    config = default_llm_config()
    if config is None:
        return None
    return build_chat_model(
        config,
        tools=tools,
        system_prompt=system_prompt if system_prompt is not None else load_system_prompt(),
    )


def build_model_for(config: LlmConfig, *, tools: Sequence[Any] | None = None) -> LlmChatModel:
    """임의 `LlmConfig`로 챗 모델을 조립(기본 system prompt 주입) — per-request 선택용(ADR-0011 §4)."""
    return build_chat_model(config, tools=tools, system_prompt=load_system_prompt())


__all__ = [
    "LlmConfig",
    "LlmChatModel",
    "build_chat_model",
    "default_llm_config",
    "build_default_chat_model",
    "build_model_for",
    "generate_title",
]
