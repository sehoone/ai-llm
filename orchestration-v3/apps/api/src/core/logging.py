"""로깅 설정 — 콘솔/JSON 포맷 전환 + 요청 상관관계 contextvar (ADR-0031).

core 소유. engine·domains는 `logging.getLogger(__name__)`만 쓰고 이 모듈을 import하지 않는다
(설정에 무지 — ADR-0005 경계). main.py가 기동 시 `configure_logging()`을 1회 호출한다.

요청 상관관계: 미들웨어(`core/middleware`)가 요청마다 `request_id`를, 인증 의존성이 `user_id`를
contextvar에 set한다. `ContextFilter`가 모든 LogRecord에 주입하므로 어느 모듈이든 자동으로 붙는다
(함수 시그니처로 id를 넘길 필요 없음).
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

from src.core.config import settings

# 요청 단위 상관관계 — 설정 전/미들웨어 밖(스케줄러·백그라운드 태스크)에서는 "-"(기본).
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")

# JSON 직렬화에서 제외할 LogRecord 표준 속성 — 나머지 __dict__ 키는 extra로 보고 병합한다.
_RESERVED = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "message", "module", "msecs", "msg", "name",
    "pathname", "process", "processName", "relativeCreated", "stack_info", "thread",
    "threadName", "taskName", "request_id", "user_id",
    "litellm_redacted",  # litellm이 레코드에 주입하는 non-serializable 센티넬 — JSON에서 제외.
}

# 서드파티 로거 억제 — 앱이 DEBUG여도 이들은 WARNING 고정(DEBUG 모드 가독성). litellm은 LLM 디버깅이
# 필요하면 개별적으로 올린다. asyncio/LiteLLM은 DEBUG에서 특히 수다스러워 플러딩을 막는다.
_NOISY_LOGGERS = (
    "httpx", "httpcore", "sqlalchemy.engine", "apscheduler", "python_multipart",
    "asyncio", "litellm", "LiteLLM",
)


class ContextFilter(logging.Filter):
    """모든 레코드에 request_id·user_id를 주입 (contextvar → LogRecord 속성)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """한 줄 JSON — Loki에서 필드 쿼리 가능. extra 필드·예외 스택을 병합한다."""

    def format(self, record: logging.LogRecord) -> str:
        ts = (
            datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        data: dict[str, object] = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            # 스레드/태스크 식별 — sync 핸들러는 스레드풀, async는 이벤트 루프 Task에서 실행.
            "thread": record.thread,
            "thread_name": record.threadName,
        }
        task_name = getattr(record, "taskName", None)
        if task_name:
            data["task_name"] = task_name
        # logger.info(..., extra={...})로 넘어온 커스텀 필드 병합 (현재 유실되던 값들 — ADR-0031 §B).
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in data:
                data[key] = value
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            data["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(data, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """루트 로거를 설정 (basicConfig 대체). log_format=console|json, log_level로 조절.

    멱등 — 핸들러를 교체하므로 중복 호출해도 핸들러가 누적되지 않는다.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())
    if settings.log_format.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        # 콘솔(로컬 dev) — 평문 + [request_id|threadName]. (ContextFilter가 record.request_id를 보장.)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [%(request_id)s|%(threadName)s]: %(message)s"
            )
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(handler)

    # 서드파티 로거 길들이기 (ADR-0031 §D) — 앱이 DEBUG여도 이들은 WARNING 고정.
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    # uvicorn 기본 access 로그는 앱 액세스 로그 미들웨어로 대체 → 중복 억제.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
