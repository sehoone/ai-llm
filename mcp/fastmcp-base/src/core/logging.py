import functools
import inspect
import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone

_BUILTIN_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno",
    "pathname", "filename", "module", "exc_info", "exc_text",
    "stack_info", "lineno", "funcName", "created", "msecs",
    "relativeCreated", "thread", "threadName", "processName",
    "process", "taskName", "message", "asctime",
})


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        from src.core.context import request_id_var
        entry: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }

        if record.exc_info:
            entry["exc"] = traceback.format_exception(*record.exc_info)

        for key, val in record.__dict__.items():
            if key not in _BUILTIN_ATTRS and not key.startswith("_"):
                try:
                    json.dumps(val)
                    entry[key] = val
                except (TypeError, ValueError):
                    entry[key] = str(val)

        return json.dumps(entry, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        try:
            from src.core.config import get_settings
            level = getattr(logging, get_settings().log_level.upper(), logging.INFO)
        except Exception:
            level = logging.INFO
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger


def tool_logger(logger_instance, *, param_keys: list[str] | None = None):
    """MCP 도구에 tool_start / tool_done / tool_error 로그 추가 데코레이터.
    Usage:
        @tool_logger(logger, param_keys=["city", "country_code"])
        async def get_weather(city: str, ...):
            ...
    """
    def decorator(fn):
        _sig = inspect.signature(fn)

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            bound = _sig.bind(*args, **kwargs)
            bound.apply_defaults()

            base_extra: dict = {"tool": fn.__name__}
            if param_keys:
                for k in param_keys:
                    if k in bound.arguments:
                        base_extra[k] = bound.arguments[k]

            logger_instance.info("tool_start", extra=base_extra)
            t0 = time.perf_counter()

            try:
                result = await fn(*args, **kwargs)
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                logger_instance.info(
                    "tool_done",
                    extra={**base_extra, "status": "success", "duration_ms": duration_ms},
                )
                return result
            except Exception as exc:
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                # ToolError는 예상된 실패 — warning 기록, stack trace 생략
                if type(exc).__name__ == "ToolError":
                    logger_instance.warning(
                        "tool_error",
                        extra={**base_extra, "status": "error", "duration_ms": duration_ms, "error": str(exc)},
                    )
                else:
                    logger_instance.exception(
                        "tool_exception",
                        extra={**base_extra, "status": "exception", "duration_ms": duration_ms},
                    )
                raise

        return wrapper
    return decorator
