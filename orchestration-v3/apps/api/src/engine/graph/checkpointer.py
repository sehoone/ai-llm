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
    """AsyncPostgresSaver + 전용 psycopg 풀을 연다 (ADR-0028).

    반환: `(saver, pool)` — pool은 shutdown 시 `await pool.close()` 용. conninfo는 도메인이 주입
    (psycopg DSN — SQLAlchemy URL 아님).

    ⚠️ **DDL(테이블 생성)은 `deploy/postgres/init.sql`로만 관리**한다 — `saver.setup()`을 호출하지 않는다.
    런타임 DDL을 없애 다중 인스턴스 기동 경쟁(동시 DDL)을 원천 제거(ADR-0028 개정 / ADR-0029 §A).
    체크포인트 테이블(`checkpoints`·`checkpoint_blobs`·`checkpoint_writes`·`checkpoint_migrations`)이
    `llmonl`에 **선재해야** 한다. langgraph-checkpoint-postgres 업그레이드 시 init.sql 블록을 동기화할 것.
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
            "options": "-csearch_path=llmonl,public",  # core/db와 동일 — llmonl의 테이블을 사용
        },
    )
    await pool.open()
    saver = AsyncPostgresSaver(pool)  # setup() 미호출 — 테이블은 init.sql이 준비(ADR-0028 개정)
    return saver, pool
