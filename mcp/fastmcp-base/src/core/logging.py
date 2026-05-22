import functools
import inspect
import logging
import sys
import time
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from src.core.context import request_id_var

# ── Request context ────────────────────────────────────────────────────────

_request_context: ContextVar[dict[str, Any]] = ContextVar("request_context", default={})


def bind_context(**kwargs: Any) -> None:
    """현재 요청에 컨텍스트 변수를 바인딩합니다."""
    current = _request_context.get()
    _request_context.set({**current, **kwargs})


def clear_context() -> None:
    """현재 요청의 모든 컨텍스트 변수를 초기화합니다."""
    _request_context.set({})


def get_context() -> dict[str, Any]:
    """현재 로깅 컨텍스트를 반환합니다."""
    return _request_context.get()


def _add_request_context(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict["request_id"] = request_id_var.get()
    ctx = get_context()
    if ctx:
        event_dict.update(ctx)
    return event_dict


# ── File handler ───────────────────────────────────────────────────────────

class JsonlFileHandler(logging.Handler):
    """일별 JSONL 파일 핸들러."""

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            self.handleError(record)


# ── Logging setup ──────────────────────────────────────────────────────────

_configured = False


def setup_logging() -> None:
    """structlog 기반 로깅을 초기화합니다.

    로컬 환경: 컬러 콘솔 출력 + JSONL 파일
    개발/프로덕션: JSON 콘솔 출력 + JSONL 파일
    """
    global _configured
    if _configured:
        return

    try:
        from src.core.config import get_settings
        settings = get_settings()
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
        log_dir: Path = settings.log_dir
        app_env: str = settings.app_env
        log_format: str = settings.log_format or (
            "console" if app_env == "local" else "json"
        )
    except Exception:
        log_level = logging.INFO
        log_dir = Path("logs")
        app_env = "local"
        log_format = "console"

    log_dir.mkdir(parents=True, exist_ok=True)

    # 공통 전처리 체인 (최종 렌더러 전 단계)
    shared_pre_chain = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _add_request_context,
    ]

    # structlog 설정 — ProcessorFormatter와 연동
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_pre_chain,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 콘솔 렌더러: 로컬은 컬러 출력, 그 외는 JSON
    console_renderer = (
        structlog.dev.ConsoleRenderer()
        if log_format == "console"
        else structlog.processors.JSONRenderer()
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=console_renderer,
            foreign_pre_chain=shared_pre_chain,
        )
    )

    # 파일 핸들러 — 환경 무관하게 항상 JSONL
    log_file = log_dir / f"{app_env}-{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    file_handler = JsonlFileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_pre_chain,
        )
    )

    # 루트 로거 설정
    logging.basicConfig(level=log_level, handlers=[console_handler, file_handler])
    logging.getLogger().setLevel(log_level)

    # uvicorn 로그가 루트로 전파되어 이중 출력되는 것 방지
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).propagate = False

    # 서드파티 로거 노이즈 억제
    for name in ("httpx", "httpcore", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)

    _configured = True


# ── Public API ─────────────────────────────────────────────────────────────

setup_logging()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """이름이 바인딩된 structlog 로거를 반환합니다."""
    return structlog.get_logger(name)


def tool_logger(logger_instance, *, param_keys: list[str] | None = None):
    """MCP 도구 함수에 tool_start / tool_done / tool_error 로그를 자동으로 추가하는 데코레이터.

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

            logger_instance.info("tool_start", **base_extra)
            t0 = time.perf_counter()

            try:
                result = await fn(*args, **kwargs)
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                logger_instance.info(
                    "tool_done",
                    **{**base_extra, "status": "success", "duration_ms": duration_ms},
                )
                return result
            except Exception as exc:
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                if type(exc).__name__ == "ToolError":
                    logger_instance.warning(
                        "tool_error",
                        **{**base_extra, "status": "error", "duration_ms": duration_ms, "error": str(exc)},
                    )
                else:
                    logger_instance.exception(
                        "tool_exception",
                        **{**base_extra, "status": "exception", "duration_ms": duration_ms},
                    )
                raise

        return wrapper
    return decorator
