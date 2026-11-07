"""TraceContext → LangChain/LangGraph RunnableConfig 빌더 (ADR-0007).

도메인 서비스는 engine의 LLM/그래프 호출에 이 config를 넘긴다. 비활성 시 빈 dict를 반환하므로
호출부에 분기가 필요 없다.
"""

from __future__ import annotations

from typing import Any

from src.core.config import settings
from src.engine.observability.context import TraceContext
from src.engine.observability.langfuse import new_callback_handler


def build_run_config(trace: TraceContext | None = None) -> dict[str, Any]:
    """RunnableConfig(`{callbacks, metadata, tags}`) 생성.

    langfuse 3.x는 metadata의 `langfuse_session_id`/`langfuse_user_id` 키를 읽어 세션·사용자를
    트레이스에 귀속한다. 관측 비활성 시 `{}` 반환.
    """
    handler = new_callback_handler()
    if handler is None:
        return {}

    metadata: dict[str, Any] = {"environment": settings.app_env}
    if trace is not None:
        if trace.session_id is not None:
            metadata["langfuse_session_id"] = trace.session_id
        if trace.user_id is not None:
            metadata["langfuse_user_id"] = str(trace.user_id)
        if trace.tags:
            # langfuse 3.x langchain 핸들러는 metadata["langfuse_tags"](list)에서 태그를 읽는다.
            metadata["langfuse_tags"] = list(trace.tags)
        metadata.update(trace.extra)

    return {"callbacks": [handler], "metadata": metadata}
