"""문서/질문 키워드 추출 (순수 LLM + JSON). V2 ai_overview 서비스 프롬프트 계승.

`generate_keywords`: 문서에서 핵심 키워드 + 동의어를 구조화 추출.
`extract_query_keywords`: 검색 질문에서 검색 키워드를 추출(실패 시 질문 원문 폴백).
LLM 설정은 도메인이 `llm_resource`를 해석해 `LlmConfig`로 주입(engine은 DB 미조회 — ADR-0005).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from src.engine.llm.config import LlmConfig
from src.engine.llm.model import build_chat_model

logger = logging.getLogger(__name__)

_CONTENT_LIMIT = 8000

_KEYWORD_PROMPT_DEFAULT = """문서에서 검색에 사용될 핵심 키워드와 동의어를 추출하세요.

추출 기준:
- 핵심 명사, 업무 용어, 고유 명사 중심
- 동의어는 같은 개념의 다른 표현(약어, 한자어, 영문 혼용 등)"""

_KEYWORD_FORMAT = """반드시 다음 JSON 형식만 반환하세요 (설명 없이):
{
  "keywords": ["키워드1", "키워드2"],
  "synonyms": {
    "키워드1": ["동의어A", "동의어B"],
    "키워드2": ["동의어C"]
  }
}"""

_QUERY_EXTRACT_SYSTEM = """사용자 질문에서 검색 키워드를 추출하세요.
핵심 명사와 핵심 개념만 추출하여 2~6개 키워드를 반환하세요.

반드시 다음 JSON 형식만 반환하세요:
{"keywords": ["키워드1", "키워드2"]}"""


@dataclass(slots=True)
class KeywordExtraction:
    """문서 키워드 추출 결과 — keyword 목록 + keyword별 동의어."""

    keywords: list[str] = field(default_factory=list)
    synonyms: dict[str, list[str]] = field(default_factory=dict)


def _message_text(content: object) -> str:
    """LLM 응답 content(문자열 또는 블록 리스트)를 평문으로 정규화."""
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in content
        )
    return str(content)


def _parse_llm_json(raw: str) -> dict:
    """```json 코드펜스를 벗겨내고 JSON 파싱."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def generate_keywords(
    title: str,
    content: str,
    config: LlmConfig,
    *,
    system_prompt: str | None = None,
) -> KeywordExtraction:
    """문서 제목·내용에서 키워드와 동의어를 추출(동기 1-shot). 파싱 실패 시 예외 전파."""
    prompt_base = system_prompt.strip() if system_prompt and system_prompt.strip() else _KEYWORD_PROMPT_DEFAULT
    full_system_prompt = f"{prompt_base}\n\n{_KEYWORD_FORMAT}"

    model = build_chat_model(config, system_prompt=None)
    resp = model.invoke(
        [
            SystemMessage(content=full_system_prompt),
            HumanMessage(content=f"문서 제목: {title}\n\n문서 내용:\n{content[:_CONTENT_LIMIT]}"),
        ]
    )
    data = _parse_llm_json(_message_text(resp.content))
    return KeywordExtraction(
        keywords=[k for k in data.get("keywords", []) if isinstance(k, str)],
        synonyms={
            k: [s for s in v if isinstance(s, str)]
            for k, v in (data.get("synonyms", {}) or {}).items()
            if isinstance(v, list)
        },
    )


def extract_query_keywords(query: str, config: LlmConfig) -> list[str]:
    """검색 질문에서 키워드 추출. 실패 시 질문 원문을 단일 키워드로 폴백(검색 중단 방지)."""
    try:
        model = build_chat_model(config, system_prompt=None)
        resp = model.invoke(
            [SystemMessage(content=_QUERY_EXTRACT_SYSTEM), HumanMessage(content=query)]
        )
        data = _parse_llm_json(_message_text(resp.content))
        keywords = [k.strip() for k in data.get("keywords", []) if isinstance(k, str) and k.strip()]
        return keywords or [query]
    except Exception:
        logger.warning("ai_overview_query_keyword_extract_failed", exc_info=True)
        return [query]
