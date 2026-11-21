"""LangGraph 체크포인터 팩토리 (ADR-0008 §2 / ADR-0028).

- 기본은 `InMemorySaver`(인프로세스) — 단일 인스턴스·테스트·로컬.
- `postgres` 모드는 `AsyncPostgresSaver`로 `llmonl` 스키마에 영속 → 재시작·다중 인스턴스에서
  HITL 승인·되묻기·중단 세션 재개가 내구적(ADR-0028).

engine 규칙(ADR-0005): FastAPI·domains 비의존. DB 좌표(conninfo)는 **도메인이 값으로 주입**한다.
postgres 풀은 이벤트 루프·비동기 open이 필요해 **import 시점이 아니라 lifespan에서** 열어야 하므로
전용 async 팩토리(`open_postgres_checkpointer`)로 분리한다.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver


def build_checkpointer() -> BaseCheckpointSaver:
    """동기 InMemory 체크포인터. import 시점 그래프 조립용 — 설정과 무관하게 항상 메모리.

    postgres 모드는 `open_postgres_checkpointer`로 lifespan에서 별도 조립해 그래프를 교체한다(ADR-0028).
    """
    return InMemorySaver()


async def open_postgres_checkpointer(conninfo: str) -> tuple[BaseCheckpointSaver, Any]:
    """AsyncPostgresSaver + 전용 psycopg 풀을 열고 체크포인트 테이블을 setup한다 (ADR-0028).

    반환: `(saver, pool)` — pool은 shutdown 시 `await pool.close()` 용. conninfo는 도메인이 주입
    (psycopg DSN — SQLAlchemy URL 아님). 테이블은 search_path로 `llmonl`에 생성된다.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    pool = AsyncConnectionPool(
        conninfo,
        open=False,
        kwargs={
            "autocommit": True,          # AsyncPostgresSaver 요구
            "row_factory": dict_row,     # AsyncPostgresSaver 요구
            "prepare_threshold": 0,      # 풀러 환경 prepared-statement 충돌 방지
            "options": "-csearch_path=llmonl,public",  # core/db와 동일 — 테이블을 llmonl에
        },
    )
    await pool.open()
    saver = AsyncPostgresSaver(pool)
    await saver.setup()  # checkpoints·checkpoint_blobs·checkpoint_writes·checkpoint_migrations (llmonl)
    return saver, pool
