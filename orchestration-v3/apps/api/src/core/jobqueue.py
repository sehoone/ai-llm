"""작업 큐 기본 연산 — Postgres SELECT … FOR UPDATE SKIP LOCKED (ADR-0032 Phase 2).

도메인·엔진을 모르는 순수 DB 인프라(core). 장기 작업(meeting 전사·요약 등)을 API 프로세스에서
분리해 재시작 내구·재시도·레플리카 분산을 얻는다. 핸들러 디스패치(job_type → 도메인 함수)는 core가
아니라 상위(`src/worker.py`)가 소유한다(레이어 경계: core는 domains를 import하지 않는다).

claim은 `FOR UPDATE SKIP LOCKED`로 다중 워커가 경합 없이 서로 다른 작업을 집어간다. 크래시 복구는
visibility timeout(`locked_at`) 초과 running 작업을 재큐잉해서 처리한다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from sqlalchemy import text

from src.core.db import engine

logger = logging.getLogger(__name__)


@dataclass
class Job:
    id: int
    job_type: str
    payload: dict
    attempts: int
    max_attempts: int


def enqueue(job_type: str, payload: dict | None = None, *, max_attempts: int = 3) -> int:
    """작업을 큐에 넣고 id를 반환. payload는 JSONB로 직렬화."""
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "INSERT INTO llmonl.job_queue (job_type, payload, max_attempts) "
                "VALUES (:t, CAST(:p AS jsonb), :m) RETURNING id"
            ),
            {"t": job_type, "p": json.dumps(payload or {}), "m": max_attempts},
        ).scalar_one()
    logger.info("job_enqueued job_id=%s job_type=%s", row, job_type)
    return int(row)


def claim_one() -> Job | None:
    """실행 가능한 작업 1건을 원자적으로 claim(SKIP LOCKED) — running 전이 + attempts 증가.

    여러 워커가 동시에 호출해도 서로 다른 행을 집어간다(락 경합 없음). 없으면 None.
    """
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "WITH job AS ("
                "  SELECT id FROM llmonl.job_queue"
                "  WHERE status = 'queued' AND run_after <= NOW()"
                "  ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1"
                ") "
                "UPDATE llmonl.job_queue q "
                "SET status = 'running', locked_at = NOW(), "
                "    attempts = attempts + 1, updated_at = NOW() "
                "FROM job WHERE q.id = job.id "
                "RETURNING q.id, q.job_type, q.payload, q.attempts, q.max_attempts"
            )
        ).mappings().first()
    if row is None:
        return None
    payload = row["payload"]
    if isinstance(payload, str):  # 드라이버에 따라 text로 올 수 있어 방어적 파싱
        payload = json.loads(payload)
    return Job(
        id=row["id"],
        job_type=row["job_type"],
        payload=payload or {},
        attempts=row["attempts"],
        max_attempts=row["max_attempts"],
    )


def mark_done(job_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE llmonl.job_queue SET status='done', updated_at=NOW() WHERE id=:i"),
            {"i": job_id},
        )


def mark_failed(job: Job, error: str, *, backoff_seconds: int = 60) -> None:
    """실패 처리 — attempts<max면 backoff 후 재큐잉, 아니면 failed로 종료."""
    retry = job.attempts < job.max_attempts
    with engine.begin() as conn:
        if retry:
            conn.execute(
                text(
                    "UPDATE llmonl.job_queue SET status='queued', last_error=:e, "
                    "run_after = NOW() + make_interval(secs => :b), "
                    "locked_at=NULL, updated_at=NOW() WHERE id=:i"
                ),
                {"e": error[:2000], "b": backoff_seconds, "i": job.id},
            )
        else:
            conn.execute(
                text(
                    "UPDATE llmonl.job_queue SET status='failed', last_error=:e, updated_at=NOW() "
                    "WHERE id=:i"
                ),
                {"e": error[:2000], "i": job.id},
            )
    logger.warning(
        "job_failed job_id=%s job_type=%s attempts=%s retry=%s",
        job.id, job.job_type, job.attempts, retry,
    )


def requeue_stuck(visibility_timeout_seconds: int) -> int:
    """running인 채 timeout을 넘긴 작업(크래시한 워커가 잡고 있던 것)을 queued로 되돌린다."""
    with engine.begin() as conn:
        n = conn.execute(
            text(
                "UPDATE llmonl.job_queue SET status='queued', locked_at=NULL, updated_at=NOW() "
                "WHERE status='running' AND locked_at < NOW() - make_interval(secs => :t)"
            ),
            {"t": visibility_timeout_seconds},
        ).rowcount
    if n:
        logger.warning("job_requeued_stuck count=%s", n)
    return n
