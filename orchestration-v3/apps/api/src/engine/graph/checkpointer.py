"""LangGraph 체크포인터 팩토리 (ADR-0008 §2).

현재는 `InMemorySaver`(인프로세스) — 단일 인스턴스 전제. 스케일아웃 시
`langgraph-checkpoint-postgres`를 도입해 `llmonl` 스키마에 영속한다(후속).
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver


def build_checkpointer(kind: str = "memory") -> BaseCheckpointSaver:
    if kind == "postgres":
        # 후속: langgraph-checkpoint-postgres 도입 후 AsyncPostgresSaver 연결.
        raise NotImplementedError(
            "postgres 체크포인터는 아직 미구현 — 'langgraph-checkpoint-postgres' 도입 필요 (ADR-0008 후속)."
        )
    return InMemorySaver()
