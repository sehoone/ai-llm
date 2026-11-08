"""근거 기반 AI Overview 답변 스트리밍 (순수 async). V2 search_service 프롬프트 계승.

검색된 사내 문서(sources)를 컨텍스트로 LLM 답변을 토큰 단위로 스트리밍한다. provider 중립
(LiteLLM) — engine/rag가 litellm.embedding을 직접 쓰는 것과 동일한 규약.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Sequence

import litellm

from src.engine.llm.config import LlmConfig

logger = logging.getLogger(__name__)

_CONTEXT_PER_DOC = 2000

_OVERVIEW_SYSTEM = """당신은 사내 AI Overview 어시스턴트입니다.
사용자 질문에 대해 검색된 사내 문서를 기반으로 정확하고 유용한 답변을 제공하세요.

규칙:
- 검색된 문서가 있으면 해당 내용 기반으로 답변하고 출처를 [문서명]으로 표시하세요
- 문서가 없거나 관련 내용이 없으면 일반 지식으로 답변하되 "사내 데이터 없음"을 명시하세요
- 답변은 간결하고 구조화되게 작성하세요 (마크다운 사용)"""


def _build_user_message(query: str, sources: Sequence[dict]) -> str:
    parts = [f"[{s['title']}]\n{str(s.get('content', ''))[:_CONTEXT_PER_DOC]}" for s in sources]
    context_str = "\n\n---\n\n".join(parts) if parts else "관련 사내 문서 없음"
    return f"질문: {query}\n\n사내 문서:\n{context_str}"


async def stream_answer(
    query: str,
    sources: Sequence[dict],
    config: LlmConfig,
    *,
    system_prompt: str | None = None,
) -> AsyncIterator[str]:
    """질문 + 근거 문서로 LLM 답변을 토큰 스트리밍. 각 yield는 답변 조각 텍스트.

    예외는 호출부(domain)가 NDJSON error 이벤트로 변환하도록 전파한다.
    """
    effective_prompt = system_prompt.strip() if system_prompt and system_prompt.strip() else _OVERVIEW_SYSTEM

    params: dict = {
        "model": config.model_id,
        "messages": [
            {"role": "system", "content": effective_prompt},
            {"role": "user", "content": _build_user_message(query, sources)},
        ],
        "stream": True,
    }
    if config.api_key:
        params["api_key"] = config.api_key
    if config.api_base:
        params["api_base"] = config.api_base
    if config.api_version:
        params["api_version"] = config.api_version
    if not config.is_reasoning and config.temperature is not None:
        params["temperature"] = config.temperature

    response = await litellm.acompletion(**params)
    async for chunk in response:
        delta = chunk.choices[0].delta
        content = getattr(delta, "content", None)
        if content:
            yield content
