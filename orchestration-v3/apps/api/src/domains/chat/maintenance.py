"""chat 유지보수 잡 (ADR-0029 §B) — 승인 만료 스윕.

주기 실행(APScheduler, ADR-0019 패턴 재사용)으로 방치된 PENDING 승인을 EXPIRED로 정리한다.
다중 인스턴스 안전: `pg_try_advisory_lock`으로 한 인스턴스만 스윕(중복 방지).

도메인 소유(ADR-0005): 스케줄은 AI 연산이 아니라 인프라 트리거. APScheduler는 선택 의존(lazy import,
미설치 시 graceful no-op — workflow 스케줄러와 동일 철학).

후속(ADR-0029): 체크포인트 보존(고아·비활성 thread) 스윕을 이 잡에 추가.
"""

from __future__ import annotations

import logging
from datetime import datetime

from src.core.config import settings

logger = logging.getLogger(__name__)

# 전역 advisory lock 키(스윕 중복 방지). 다른 advisory lock과 충돌하지 않도록 고정 상수로 관리.
_SWEEP_LOCK_KEY = 290_001  # ADR-0029 chat maintenance sweep


async def run_maintenance() -> None:
    """유지보수 1회 — 만료 승인 스윕. 한 인스턴스만 수행(advisory lock).

    **트랜잭션 레벨** advisory lock(`pg_try_advisory_xact_lock`)을 쓴다 — 커밋/세션 종료 시 자동 해제되어
    명시 unlock·락 누수가 없다(세션 레벨 락은 repo의 commit으로 커넥션이 반환되며 누수됨).
    """
    from sqlalchemy import text
    from sqlmodel import Session

    from src.core.db import engine
    from src.domains.auth.repository import RevokedTokenRepository
    from src.domains.chat.repository import ChatRepository

    with Session(engine) as session:
        acquired = session.connection().execute(
            text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": _SWEEP_LOCK_KEY}
        ).scalar()
        if not acquired:
            return  # 다른 인스턴스가 스윕 중 — skip (트랜잭션 종료 시 lock 자동 해제)
        now = datetime.utcnow()
        try:
            n = ChatRepository(session).expire_pending_approvals(now)
            if n:
                logger.info("chat_maintenance_expired_approvals count=%s", n)
            # 폐기 토큰 블랙리스트 만료분 정리 (ADR-0032 Phase 2) — 앱 공통 유지보수.
            r = RevokedTokenRepository(session).delete_expired(now)
            if r:
                logger.info("revoked_token_cleanup count=%s", r)
        except Exception:
            logger.exception("chat_maintenance_failed")


class ChatMaintenanceScheduler:
    """프로세스 싱글톤 — 유지보수 잡을 cron으로 구동 (ADR-0029)."""

    def __init__(self) -> None:
        self._scheduler = None  # AsyncIOScheduler | None

    def start(self) -> None:
        if not settings.chat_maintenance_enabled:
            logger.info("chat_maintenance_disabled (settings)")
            return
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            logger.warning("apscheduler not installed — chat maintenance will not run")
            return
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._scheduler.add_job(
            run_maintenance,
            CronTrigger.from_crontab(settings.chat_maintenance_cron, timezone="UTC"),
            id="chat_maintenance",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("chat_maintenance_scheduler_started cron=%s", settings.chat_maintenance_cron)

    def shutdown(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None


chat_maintenance_scheduler = ChatMaintenanceScheduler()
