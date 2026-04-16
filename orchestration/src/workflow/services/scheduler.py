"""APScheduler integration for cron-triggered workflows.

Uses AsyncIOScheduler with a CronTrigger to fire workflow executions.
The scheduler is started in the FastAPI lifespan and shut down cleanly on exit.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session

from src.common.logging import logger
from src.common.services.database import database_service
from src.workflow.models.schedule_model import WorkflowSchedule
from src.workflow.services.executor.engine import workflow_engine


class WorkflowScheduler:
    """Singleton that owns the APScheduler instance and syncs it with the DB."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(timezone="UTC")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the scheduler and load all active schedules from DB."""
        self._scheduler.start()
        self._load_all_from_db()
        logger.info("workflow_scheduler_started")

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("workflow_scheduler_stopped")

    # ── Public operations ─────────────────────────────────────────────────────

    def add_schedule(self, schedule: WorkflowSchedule) -> None:
        """Register (or replace) a job for the given schedule."""
        self._upsert_job(schedule)

    def remove_schedule(self, schedule_id: str) -> None:
        """Remove the job for the given schedule ID."""
        try:
            self._scheduler.remove_job(schedule_id)
        except Exception:
            pass  # not found — already gone

    def pause_schedule(self, schedule_id: str) -> None:
        try:
            self._scheduler.pause_job(schedule_id)
        except Exception:
            pass

    def resume_schedule(self, schedule_id: str) -> None:
        try:
            self._scheduler.resume_job(schedule_id)
        except Exception:
            pass

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_all_from_db(self) -> None:
        with Session(database_service.engine) as db:
            schedules = database_service.list_all_active_schedules(db)
        for sched in schedules:
            self._upsert_job(sched)
        logger.info("workflow_schedules_loaded", count=len(schedules))

    def _upsert_job(self, schedule: WorkflowSchedule) -> None:
        try:
            parts = schedule.cron_expr.strip().split()
            if len(parts) != 5:
                logger.warning("invalid_cron_expr", schedule_id=schedule.id, expr=schedule.cron_expr)
                return

            minute, hour, day, month, day_of_week = parts
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone="UTC",
            )

            # Replace existing job if any
            if self._scheduler.get_job(schedule.id):
                self._scheduler.remove_job(schedule.id)

            self._scheduler.add_job(
                func=_fire_workflow,
                trigger=trigger,
                id=schedule.id,
                args=[schedule.workflow_id, schedule.user_id, schedule.input_data],
                replace_existing=True,
                misfire_grace_time=300,
            )

            if not schedule.is_active:
                self._scheduler.pause_job(schedule.id)

            logger.info("schedule_job_registered", schedule_id=schedule.id, cron=schedule.cron_expr)
        except Exception as exc:
            logger.error("schedule_job_register_failed", schedule_id=schedule.id, error=str(exc))


async def _fire_workflow(workflow_id: str, user_id: int, input_data: dict[str, Any]) -> None:
    """Callback invoked by APScheduler on each cron tick."""
    logger.info("schedule_fired", workflow_id=workflow_id, user_id=user_id)
    try:
        with Session(database_service.engine) as db:
            workflow = database_service.get_workflow(db, workflow_id)
            if not workflow:
                logger.warning("scheduled_workflow_not_found", workflow_id=workflow_id)
                return
            await workflow_engine.execute(
                workflow=workflow,
                input_data=input_data,
                user_id=user_id,
                db=db,
            )
    except Exception as exc:
        logger.error("scheduled_workflow_failed", workflow_id=workflow_id, error=str(exc), exc_info=True)


# Module-level singleton
workflow_scheduler = WorkflowScheduler()
