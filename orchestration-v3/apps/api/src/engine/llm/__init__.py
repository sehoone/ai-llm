"""llm: 모델 호출 추상화 (provider·chat·stream). 프로바이더 중립 — ADR-0005 / ADR-0010.

- `LlmConfig`: 순수 설정 값.
- `build_chat_model(config)` / `build_model_for(config)`: 값만으로 모델 조립.

LLM 선택(provider·model·key·endpoint)은 전적으로 `llm_resource` 테이블에서 온다.
도메인이 행을 해석해 `LlmConfig`로 주입한다(engine은 DB·env 미참조). env 기반 기본 모델 없음.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.engine.llm.config import LlmConfig
from src.engine.llm.model import LlmChatModel, build_chat_model
from src.engine.llm.summary import generate_title
from src.engine.prompts import load_system_prompt


def build_model_for(config: LlmConfig, *, tools: Sequence[Any] | None = None) -> LlmChatModel:
    """임의 `LlmConfig`로 챗 모델을 조립(기본 system prompt 주입) — per-request 선택용(ADR-0011 §4)."""
    return build_chat_model(config, tools=tools, system_prompt=load_system_prompt())


__all__ = [
    "LlmConfig",
    "LlmChatModel",
    "build_chat_model",
    "build_model_for",
    "generate_title",
]
