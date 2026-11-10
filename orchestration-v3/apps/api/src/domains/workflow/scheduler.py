"""APScheduler 래퍼 — cron 워크플로우 트리거 (ADR-0019 §4, Phase 3).

스케줄러는 AI 연산이 아니라 인프라 트리거이므로 도메인이 소유한다(engine 금지 — ADR-0005 대안 기각).
APScheduler는 선택 의존(`uv sync` 전이어도 앱이 뜨도록 **lazy import** + 미설치 시 graceful no-op).
job 발화 시 **새 Session**을 열고 `WorkflowService.execute(...)`를 돌린다(서비스는 lazy import — 순환 회피).
"""

from __future__ import annotations

import logging

from src.core.config import settings

logger = logging.getLogger(__name__)


async def _fire(schedule_id: str) -> None:
    """스케줄 job 본체 — 새 Session에서 워크플로우 1회 실행."""
    from sqlmodel import Session

    from src.core.db import engine
    from src.domains.workflow.repository import WorkflowRepository
    from src.domains.workflow.service import WorkflowService

    with Session(engine) as session:
        repo = WorkflowRepository(session)
        schedule = repo.get_schedule(schedule_id)
        if schedule is None or not schedule.is_active:
            return
        workflow = repo.get(schedule.workflow_id)
        if workflow is None:
            return
        try:
            await WorkflowService(session).execute(
                workflow, schedule.input_data or {}, schedule.user_id
            )
        except Exception:
            logger.exception("workflow_schedule_fire_failed schedule_id=%s", schedule_id)


class WorkflowScheduler:
    """프로세스 싱글톤 스케줄러 래퍼."""

    def __init__(self) -> None:
        self._scheduler = None  # AsyncIOScheduler | None

    @property
    def enabled(self) -> bool:
        return self._scheduler is not None

    def start(self) -> None:
        if not settings.workflow_scheduler_enabled:
            logger.info("workflow_scheduler_disabled (settings)")
            return
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
        except ImportError:
            logger.warning("apscheduler not installed — workflow schedules will not fire")
            return
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._scheduler.start()
        self._restore_jobs()
        logger.info("workflow_scheduler_started")

    def shutdown(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    def add_job(self, schedule_id: str, cron_expr: str) -> None:
        if self._scheduler is None:
            return
        from apscheduler.triggers.cron import CronTrigger

        trigger = CronTrigger.from_crontab(cron_expr, timezone="UTC")
        self._scheduler.add_job(
            _fire, trigger, id=schedule_id, args=[schedule_id], replace_existing=True
        )

    def remove_job(self, schedule_id: str) -> None:
        if self._scheduler is None:
            return
        try:
            self._scheduler.remove_job(schedule_id)
        except Exception:  # noqa: BLE001 — 없는 job 제거는 무시
            pass

    def _restore_jobs(self) -> None:
        """기동 시 활성 스케줄을 job으로 복원."""
        from sqlmodel import Session

        from src.core.db import engine
        from src.domains.workflow.repository import WorkflowRepository

        with Session(engine) as session:
            for s in WorkflowRepository(session).list_active_schedules():
                try:
                    self.add_job(s.id, s.cron_expr)
                except Exception:
                    logger.exception("workflow_schedule_restore_failed schedule_id=%s", s.id)


# 모듈 싱글톤
workflow_scheduler = WorkflowScheduler()
