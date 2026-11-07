"""LLM 설정 값 객체 (ADR-0010 §2).

순수 값 — DB·domains 미의존(ADR-0005). domain이 `llm_resource` 행을 해석해 이 값으로 주입하거나,
`core.config`(env)에서 기본값을 읽는다(__init__.default_llm_config).
"""

from __future__ import annotations

from dataclasses import dataclass

# 추론 모델(임의 temperature 거부) 프리픽스 — V2 _create_llm_from_resource 계승.
_REASONING_PREFIXES = ("gpt-5", "o1", "o3")


@dataclass(frozen=True, slots=True)
class LlmConfig:
    """단일 LLM 호출 설정. provider별 `model_id`는 LiteLLM 관례를 따른다(ADR-0010 §1)."""

    provider: str = "openai"  # openai | azure | anthropic | google | ollama
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    api_base: str | None = None
    api_version: str | None = None  # azure
    temperature: float | None = 0.7
    max_tokens: int | None = None

    @property
    def model_id(self) -> str:
        """LiteLLM `model` 식별자."""
        if self.provider == "azure":
            return f"azure/{self.model}"
        if self.provider == "anthropic":
            return f"anthropic/{self.model}"
        if self.provider == "google":
            return f"gemini/{self.model}"
        if self.provider == "ollama":
            return f"ollama/{self.model}"
        return self.model  # openai / 기타

    @property
    def is_reasoning(self) -> bool:
        """gpt-5·o1·o3 계열 — temperature 미지원."""
        m = self.model.lower()
        return any(m == p or m.startswith(p) for p in _REASONING_PREFIXES)
