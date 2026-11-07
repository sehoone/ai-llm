"""Langfuse 클라이언트 래퍼 (ADR-0007).

engine은 `core.config`만 의존한다(ADR-0005 허용 방향). FastAPI·domains는 import하지 않는다.
관측은 **best-effort** — 초기화/전송 실패가 요청 처리를 깨지 않는다(로깅 후 조용히 비활성).
"""

from __future__ import annotations

import logging

from src.core.config import settings

logger = logging.getLogger(__name__)

_client = None  # langfuse.Langfuse 싱글턴 (지연 생성)


def is_enabled() -> bool:
    return settings.langfuse_is_enabled


def _client_singleton():
    """설정값으로 Langfuse 싱글턴을 지연 생성. 실패 시 None."""
    global _client
    if _client is None:
        from langfuse import Langfuse  # 지연 import — 비활성 환경·테스트에서 의존성 강제 안 함

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return _client


def new_callback_handler():
    """LangChain/LangGraph용 CallbackHandler 생성. 비활성/실패 시 None.

    langfuse 3.x는 요청마다 새 핸들러를 쓰는 것을 권장(싱글턴 클라이언트를 공유).
    """
    if not settings.langfuse_is_enabled:
        return None
    try:
        _client_singleton()  # 자격증명으로 싱글턴 보장
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()
    except Exception as e:  # noqa: BLE001 — 관측 누락은 요청을 깨면 안 됨
        logger.warning("langfuse CallbackHandler 생성 실패 (관측 비활성): %s", e)
        return None


def shutdown() -> None:
    """프로세스 종료 훅에서 호출 — 버퍼된 트레이스를 flush (FastAPI lifespan에서 사용)."""
    if _client is None:
        return
    try:
        _client.flush()
    except Exception as e:  # noqa: BLE001
        logger.warning("langfuse flush 실패: %s", e)
