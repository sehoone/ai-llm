"""장기 메모리 — mem0 + pgvector 래퍼 (ADR-0005 / ADR-0015).

opt-in·비차단: 미설정·init 오류·mem0 미설치는 모두 삼켜 chat을 막지 않는다(빈 결과). mem0는 지연
import하여 비활성 시 startup을 깨지 않는다. 사용자 id·쿼리는 도메인이 값으로 주입.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from src.core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_memory: Any = None
_init_failed = False


def is_enabled() -> bool:
    """메모리 사용 가능 여부 — opt-in 플래그 + LLM 키(ADR-0015)."""
    return settings.memory_enabled and bool(settings.llm_api_key)


def _get_memory() -> Any:
    """지연 초기화 싱글턴. 실패 시 None(이후 재시도 안 함)."""
    global _memory, _init_failed
    if _memory is not None or _init_failed:
        return _memory
    with _lock:
        if _memory is not None or _init_failed:
            return _memory
        try:
            from mem0 import Memory
            from mem0.vector_stores.pgvector import PGVector

            # mem0가 하드코딩한 'public' 스키마 조회를 우리 스키마로 몽키패치 (V2 계승).
            schema = settings.postgres_schema

            def _list_cols(self: Any) -> list[str]:
                with self._get_cursor() as cur:
                    cur.execute(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                        (schema,),
                    )
                    return [row[0] for row in cur.fetchall()]

            PGVector.list_cols = _list_cols

            conn = (
                f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
                f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
                f"?options=-c%20search_path%3D{schema}%2Cpublic"
            )
            component = {
                "provider": "openai",
                "config": {"model": settings.memory_llm_model, "api_key": settings.llm_api_key},
            }
            embedder = {
                "provider": "openai",
                "config": {"model": settings.memory_embedder_model, "api_key": settings.llm_api_key},
            }
            _memory = Memory.from_config(
                {
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "collection_name": settings.memory_collection,
                            "connection_string": conn,
                        },
                    },
                    "llm": component,
                    "embedder": embedder,
                }
            )
            logger.info("long_term_memory_initialized")
        except Exception:
            _init_failed = True
            logger.exception("long_term_memory_init_failed")
    return _memory


def _extract_items(res: Any) -> list[dict[str, Any]]:
    if isinstance(res, dict):
        items = res.get("results", [])
    else:
        items = res or []
    return [it for it in items if isinstance(it, dict)]


def search(user_id: int, query: str, *, limit: int = 5) -> str:
    """사용자 메모리에서 쿼리 관련 항목을 bullet 문자열로. 실패 시 빈 문자열."""
    if not is_enabled() or not query:
        return ""
    mem = _get_memory()
    if mem is None:
        return ""
    try:
        # mem0 2.x: search는 top-level user_id를 거부 → filters 사용 (add/delete_all은 user_id=).
        res = mem.search(query=query, filters={"user_id": str(user_id)}, limit=limit)
        lines = [f"* {it['memory']}" for it in _extract_items(res) if it.get("memory")]
        return "\n".join(lines)
    except Exception:
        logger.exception("long_term_memory_search_failed")
        return ""


def add(user_id: int, messages: list[dict[str, str]]) -> None:
    """대화(user/assistant 텍스트)를 메모리에 추가. 비차단."""
    if not is_enabled():
        return
    mem = _get_memory()
    if mem is None:
        return
    try:
        clean = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        if clean:
            mem.add(clean, user_id=str(user_id))
    except Exception:
        logger.exception("long_term_memory_add_failed")


def delete_all(user_id: int) -> None:
    """사용자의 모든 장기 메모리 삭제."""
    mem = _get_memory()
    if mem is None:
        return
    try:
        mem.delete_all(user_id=str(user_id))
    except Exception:
        logger.exception("long_term_memory_delete_all_failed")
        raise


__all__ = ["is_enabled", "search", "add", "delete_all"]
