import asyncio
from typing import Any, Optional

from src.common.audit.models import AuditLog
from src.common.logging import logger
from src.common.services.db_session import managed_session


class AuditService:
    """감사 로그를 메인 요청 트랜잭션과 독립적으로 기록한다."""

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            from src.common.services.database import database_service
            self._engine = database_service.engine
        return self._engine

    def _sync_write(self, log: AuditLog) -> None:
        try:
            with managed_session(self._get_engine()) as session:
                session.add(log)
                session.commit()
        except Exception as e:
            logger.error("audit_write_failed", action=log.action, error=str(e))

    async def write(
        self,
        action: str,
        resource_type: str,
        user_id: Optional[int] = None,
        user_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_id: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        description: Optional[str] = None,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
    ) -> None:
        log = AuditLog(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            user_ip=user_ip,
            request_id=request_id,
            user_agent=user_agent,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            description=description,
            status=status,
            error_message=error_message[:1000] if error_message else None,
        )
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(loop.run_in_executor(None, self._sync_write, log))


audit_service = AuditService()
