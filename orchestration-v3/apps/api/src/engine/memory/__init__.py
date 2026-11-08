"""장기 메모리 — mem0 + pgvector 래퍼 (ADR-0005 / ADR-0015).

opt-in·비차단: 미설정·init 오류·mem0 미설치는 모두 삼켜 chat을 막지 않는다(빈 결과). mem0는 지연
import하여 비활성 시 startup을 깨지 않는다.

LLM·임베더 선택은 `llm_resource` 테이블에서 온다(env 미참조) — 도메인이 chat 리소스(추출 LLM)와
embedding 리소스를 해석해 `LlmConfig` 값으로 주입한다. 사용자 id·쿼리도 도메인이 값으로 주입.
"""

from __future__ import annotations

import logging
import threading
from typing import Any
from urllib.parse import urlparse

from src.core.config import settings
from src.engine.llm.config import LlmConfig

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_memory: Any = None
_init_failed = False


def is_enabled() -> bool:
    """메모리 사용 가능 여부 — opt-in 플래그(ADR-0015). LLM 좌표는 도메인이 주입한다."""
    return settings.memory_enabled


def _azure_endpoint(api_base: str | None) -> str:
    """리소스 api_base(전체 completions URL 가능)에서 Azure 베이스 엔드포인트만 추출."""
    if not api_base:
        return ""
    p = urlparse(api_base)
    return f"{p.scheme}://{p.netloc}" if p.scheme and p.netloc else api_base


def _mem0_component(cfg: LlmConfig) -> dict[str, Any]:
    """`LlmConfig` → mem0 llm/embedder 컴포넌트 설정 (provider별 — azure/openai 등)."""
    if cfg.provider == "azure":
        return {
            "provider": "azure_openai",
            "config": {
                "model": cfg.model,  # azure는 deployment 이름
                "azure_kwargs": {
                    "azure_deployment": cfg.model,
                    "api_version": cfg.api_version,
                    "azure_endpoint": _azure_endpoint(cfg.api_base),
                    "api_key": cfg.api_key,
                },
            },
        }
    config: dict[str, Any] = {"model": cfg.model, "api_key": cfg.api_key}
    if cfg.api_base:
        config["openai_base_url"] = cfg.api_base
    return {"provider": cfg.provider, "config": config}


def _get_memory(llm: LlmConfig, embedder: LlmConfig) -> Any:
    """지연 초기화 싱글턴. 최초 호출의 llm/embedder 설정으로 조립. 실패 시 None(재시도 안 함)."""
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
            _memory = Memory.from_config(
                {
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "collection_name": settings.memory_collection,
                            "connection_string": conn,
                        },
                    },
                    "llm": _mem0_component(llm),
                    "embedder": _mem0_component(embedder),
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


def search(
    user_id: int, query: str, llm: LlmConfig | None, embedder: LlmConfig | None, *, limit: int = 5
) -> str:
    """사용자 메모리에서 쿼리 관련 항목을 bullet 문자열로. 미설정/실패 시 빈 문자열."""
    if not is_enabled() or not query or llm is None or embedder is None:
        return ""
    mem = _get_memory(llm, embedder)
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


def add(
    user_id: int, messages: list[dict[str, str]], llm: LlmConfig | None, embedder: LlmConfig | None
) -> None:
    """대화(user/assistant 텍스트)를 메모리에 추가. 미설정 시 no-op. 비차단."""
    if not is_enabled() or llm is None or embedder is None:
        return
    mem = _get_memory(llm, embedder)
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


def delete_all(user_id: int, llm: LlmConfig | None, embedder: LlmConfig | None) -> None:
    """사용자의 모든 장기 메모리 삭제. 설정 없으면 no-op."""
    if llm is None or embedder is None:
        return
    mem = _get_memory(llm, embedder)
    if mem is None:
        return
    try:
        mem.delete_all(user_id=str(user_id))
    except Exception:
        logger.exception("long_term_memory_delete_all_failed")
        raise


__all__ = ["is_enabled", "search", "add", "delete_all"]
