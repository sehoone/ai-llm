"""ai_overview: 키워드 추출 + 근거 기반 답변 스트리밍 (순수) — ADR-0005.

engine은 DB·FastAPI를 모른다. 프롬프트는 작업별로 여기 둔다(engine/llm/summary.py 선례).
LLM 설정은 `LlmConfig`로 주입받고, 벡터 청킹·임베딩은 engine/rag를 재사용한다(domains/ai_overview).
"""

from __future__ import annotations

from src.engine.ai_overview.answer import stream_answer
from src.engine.ai_overview.keywords import (
    KeywordExtraction,
    extract_query_keywords,
    generate_keywords,
)

__all__ = [
    "KeywordExtraction",
    "generate_keywords",
    "extract_query_keywords",
    "stream_answer",
]
