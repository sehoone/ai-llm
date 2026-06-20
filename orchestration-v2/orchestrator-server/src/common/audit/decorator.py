import functools
from typing import Any, Callable, Optional

from src.common.audit.service import audit_service
from src.common.logging import get_context


def audit_log(action: str, resource_type: str):
    """감사 로그를 기록하는 FastAPI 엔드포인트 데코레이터.

    ContextVar에서 user_id, request_id, client_ip를 자동으로 읽는다.
    성공 시 result에서 리소스 ID를 추출하고, 실패 시 예외 메시지를 기록한다.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = get_context()
            user_id: Optional[int] = ctx.get("user_id")
            request_id: Optional[str] = ctx.get("request_id")
            client_ip: Optional[str] = ctx.get("client_ip")

            try:
                result = await func(*args, **kwargs)
                resource_id = _extract_resource_id(result)
                await audit_service.write(
                    action=action,
                    resource_type=resource_type,
                    user_id=user_id,
                    user_ip=client_ip,
                    request_id=request_id,
                    resource_id=resource_id,
                    status="SUCCESS",
                )
                return result
            except Exception as exc:
                await audit_service.write(
                    action=action,
                    resource_type=resource_type,
                    user_id=user_id,
                    user_ip=client_ip,
                    request_id=request_id,
                    status="FAILURE",
                    error_message=str(exc),
                )
                raise

        return wrapper
    return decorator


def _extract_resource_id(result: Any) -> Optional[str]:
    if result is None:
        return None
    for attr in ("id", "agent_id", "session_id", "doc_id", "workflow_id"):
        val = getattr(result, attr, None)
        if val is not None:
            return str(val)
    if isinstance(result, dict):
        for key in ("id", "agent_id", "session_id", "workflow_id"):
            val = result.get(key)
            if val is not None:
                return str(val)
    return None
