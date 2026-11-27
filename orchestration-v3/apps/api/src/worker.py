"""작업 큐 워커 — claim → 디스패치 → 완료/실패 (ADR-0032 Phase 2).

핸들러 레지스트리(job_type → 도메인 코루틴)를 소유한다. core/jobqueue는 도메인을 모르므로
(레이어 경계) 디스패치는 여기(main.py와 같은 앱 최상위)에 둔다.

두 가지로 구동된다:
  1. **in-process** — `main.py` lifespan이 `WORKER_IN_PROCESS=true`일 때 asyncio 태스크로
     `worker_loop`를 띄운다(bare-metal·단일 인스턴스 기본). SKIP LOCKED라 api 레플리카 다수도 안전.
  2. **standalone** — `python -m src.worker` (docker 전용 worker 컨테이너). api는 off.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from src.core import jobqueue
from src.core.config import settings
from src.core.jobqueue import Job
from src.core.logging import configure_logging

logger = logging.getLogger(__name__)


async def _handle_meeting_process(payload: dict) -> None:
    # 도메인 핸들러는 지연 import(레이어상 worker가 domains 위 — 순환·기동비용 회피).
    from src.domains.meeting.service import run_process_meeting

    await run_process_meeting(payload["meeting_id"])


# job_type → 핸들러. 새 장기작업은 여기에 등록.
HANDLERS: dict[str, Callable[[dict], Awaitable[None]]] = {
    "meeting_process": _handle_meeting_process,
}


async def _run_job(job: Job) -> None:
    handler = HANDLERS.get(job.job_type)
    if handler is None:
        jobqueue.mark_failed(job, f"unknown job_type: {job.job_type}", backoff_seconds=0)
        # unknown은 재시도 의미 없음 — max_attempts까지 돌지 않도록 즉시 failed 처리를 유도.
        return
    try:
        await handler(job.payload)
    except Exception as exc:  # noqa: BLE001 — 모든 핸들러 예외를 큐 실패로 흡수(워커는 계속 돈다)
        logger.exception("job_handler_error job_id=%s job_type=%s", job.id, job.job_type)
        jobqueue.mark_failed(job, f"{type(exc).__name__}: {exc}")
    else:
        jobqueue.mark_done(job.id)


async def worker_loop(stop: asyncio.Event) -> None:
    """stop이 set될 때까지 claim→실행 반복. 큐가 비면 polling 간격만큼 대기. 주기적 stuck 재큐잉."""
    logger.info("worker_loop_started poll=%ss", settings.worker_poll_interval_seconds)
    # 기동 시 1회: 크래시한 워커가 남긴 running 작업을 즉시 복구.
    await asyncio.to_thread(jobqueue.requeue_stuck, settings.job_visibility_timeout_seconds)
    last_sweep = 0.0
    while not stop.is_set():
        try:
            job = await asyncio.to_thread(jobqueue.claim_one)
            if job is not None:
                logger.info("job_claimed job_id=%s job_type=%s", job.id, job.job_type)
                await _run_job(job)
                continue  # 다음 작업을 곧바로 시도(큐 소진까지 바쁘게)
            # 큐 빔 — 대기하되, 간헐적으로 stuck 재큐잉.
            last_sweep += settings.worker_poll_interval_seconds
            if last_sweep >= settings.job_visibility_timeout_seconds:
                timeout = settings.job_visibility_timeout_seconds
                await asyncio.to_thread(jobqueue.requeue_stuck, timeout)
                last_sweep = 0.0
        except Exception:
            logger.exception("worker_loop_iteration_error")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.worker_poll_interval_seconds)
        except TimeoutError:
            pass
    logger.info("worker_loop_stopped")


def main() -> None:
    """standalone 워커 엔트리 — `python -m src.worker`."""
    configure_logging()
    stop = asyncio.Event()
    try:
        asyncio.run(worker_loop(stop))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
