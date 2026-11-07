"""대화 제목 자동생성 (ADR-0011 §3). V2 `chatbot/services/summary_service` 참조.

기본 LLM으로 첫 왕복에서 짧은 한국어 제목을 생성한다. 미구성(키 없음)·실패 시 폴백.
engine 모듈 — `domains`·FastAPI 비의존(ADR-0005).
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.engine.llm.config import LlmConfig
from src.engine.llm.model import build_chat_model

logger = logging.getLogger(__name__)

_FALLBACK = "새로운 대화"

_TITLE_PROMPT = (
    "You are a concise title generator. "
    "Given a conversation excerpt, produce a short Korean title (3-5 words). "
    "Output only the title - no quotes, no punctuation, no explanation."
)


def generate_title(user_message: str, ai_message: str, *, config: LlmConfig | None = None) -> str:
    """첫 대화 기반 짧은 제목 생성. 실패 시 폴백 반환.

    Args:
        user_message: 첫 사용자 발화.
        ai_message: 그에 대한 어시스턴트 답변.
        config: LLM 설정(미지정 시 core.config 기본값). None이면 폴백.
    """
    cfg = config or _default_config()
    if cfg is None:
        return _FALLBACK
    try:
        # 타이틀 전용 프롬프트를 메시지로 직접 주입 → 챗 system prompt는 비운다.
        model = build_chat_model(cfg, system_prompt=None)
        resp = model.invoke(
            [
                SystemMessage(content=_TITLE_PROMPT),
                HumanMessage(content=f"사용자: {user_message}\nAI: {ai_message}\n\n제목:"),
            ]
        )
        title = str(resp.content).strip().strip('"').strip("'")
        return title or _FALLBACK
    except Exception:
        logger.exception("title_generation_failed")
        return _FALLBACK


def _default_config() -> LlmConfig | None:
    # 지연 import로 순환 참조 회피 (__init__가 이 모듈을 노출).
    from src.engine.llm import default_llm_config

    return default_llm_config()
