"""샘플 08 — 관찰성 패턴 (Observability)

Routes:
    GET  /api/v1/sample/observability/log-demo      — structlog 레벨별 올바른 사용법
    POST /api/v1/sample/observability/business-op   — 서비스 레이어 로깅 패턴
    GET  /api/v1/sample/observability/context       — 미들웨어 자동 바인딩 컨텍스트
    GET  /api/v1/sample/observability/metrics-demo  — Prometheus 지표 수동 기록

학습 포인트:
    1. structlog 규칙: logger.info("이벤트명", key=value) — f-string 절대 금지
    2. 이벤트명은 snake_case 동사+명사 ("user_created", "llm_call_failed")
    3. LoggingContextMiddleware가 모든 로그에 request_id / user_id 자동 주입
    4. Prometheus: HTTP 지표는 자동, LLM/도메인 지표는 직접 측정
"""

import random
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.common.logging import bind_context, get_context, logger
from src.common.metrics import http_requests_total, llm_inference_duration_seconds

router = APIRouter()


# ── 패턴 1: structlog 레벨별 사용법 ──────────────────────────────────────────

@router.get(
    "/log-demo",
    summary="structlog 레벨별 올바른 사용법",
    description="""
structlog의 올바른 사용 패턴을 보여줍니다.

**핵심 규칙 — f-string 금지:**
```python
# ✅ 올바름: 이벤트명 + kwargs (구조화, 검색 가능)
logger.info("user_logged_in", user_id=123, ip="1.2.3.4")
logger.warning("rate_limit_near", endpoint="/chat", usage=0.85)
logger.error("llm_call_failed", model="gpt-4o", error=str(e), exc_info=True)

# ❌ 잘못됨: f-string (구조화 불가, Kibana/Loki 필터링 불가)
logger.info(f"사용자 {user_id} 로그인 성공")
```

**레벨 선택 기준:**
- `debug`: 개발 중 내부 상태 (쿼리, 토큰 수, 캐시 히트)
- `info`: 비즈니스 이벤트 (로그인, 세션 생성, 문서 업로드)
- `warning`: 예상 가능한 문제 (Circuit Breaker OPEN, fallback 발생)
- `error`: 예상 못한 실패 (DB 연결 끊김, LLM API 오류)

**JSON 출력 예시 (프로덕션):**
```json
{"event": "user_logged_in", "user_id": 123, "request_id": "req-abc",
 "timestamp": "2024-01-01T00:00:00Z", "level": "info"}
```

**실제 구현 코드:** `src/common/logging.py`
    """,
)
async def log_demo(level: str = "info"):
    valid_levels = {"debug", "info", "warning", "error"}
    if level not in valid_levels:
        raise HTTPException(400, f"level은 다음 중 하나여야 합니다: {', '.join(sorted(valid_levels))}")

    logger.debug("log_demo_debug", level_requested=level, note="개발 환경에서만 출력됨")
    logger.info("log_demo_called", level_requested=level)
    logger.warning("log_demo_warning", level_requested=level, threshold=0.8, current=0.6)

    if level == "error":
        try:
            raise ValueError("시뮬레이션된 에러 — 스택 트레이스 확인용")
        except ValueError as e:
            logger.error("log_demo_error", error=str(e), exc_info=True)

    return {
        "level_demonstrated": level,
        "rule": "logger.info('이벤트명', key=value) — f-string 금지",
        "current_logging_context": get_context(),
    }


# ── 패턴 2: 서비스 레이어 로깅 ──────────────────────────────────────────────

class BusinessOpRequest(BaseModel):
    operation: str
    payload: Optional[dict] = None


@router.post(
    "/business-op",
    summary="서비스 레이어 로깅 패턴",
    description="""
실제 서비스 코드에서의 로깅 패턴.

**시작 / 완료 / 실패 이벤트 쌍:**
```python
logger.info("session_create_started", user_id=user_id)
try:
    session = await session_service.create(user_id)
    logger.info("session_create_ok", user_id=user_id, session_id=session.id)
except Exception as e:
    logger.error("session_create_failed", user_id=user_id, error=str(e))
    raise
```

**타이밍 측정:**
```python
start = time.monotonic()
result = await expensive_operation()
elapsed_ms = (time.monotonic() - start) * 1000
logger.info("operation_ok", duration_ms=round(elapsed_ms, 2))
```

**금지 패턴:**
```python
# ❌ 로그에 민감한 정보 포함 금지
logger.info("user_login", password=plain_password)  # 절대 금지
logger.info("token_issued", token=jwt_token)         # 금지
```
    """,
)
async def business_op(body: BusinessOpRequest):
    start = time.monotonic()

    logger.info(
        "business_op_started",
        operation=body.operation,
        has_payload=body.payload is not None,
    )

    await _simulate_work()

    elapsed_ms = (time.monotonic() - start) * 1000
    logger.info(
        "business_op_completed",
        operation=body.operation,
        duration_ms=round(elapsed_ms, 2),
    )

    return {
        "operation": body.operation,
        "status": "completed",
        "duration_ms": round(elapsed_ms, 2),
    }


async def _simulate_work() -> None:
    import asyncio
    await asyncio.sleep(random.uniform(0.01, 0.05))


# ── 패턴 3: 미들웨어 컨텍스트 ────────────────────────────────────────────────

@router.get(
    "/context",
    summary="미들웨어 자동 바인딩 컨텍스트",
    description="""
`LoggingContextMiddleware`가 모든 요청에 자동 바인딩하는 컨텍스트를 확인합니다.

**미들웨어가 자동 주입하는 값 (src/common/middleware.py):**
```python
bind_context(
    request_id=request_id,  # RequestIDMiddleware가 생성한 UUID
    user_id=user_id,        # JWT 디코딩 후 추출
    session_id=session_id,  # 요청의 세션 ID
)
```

**이후 모든 로그에 자동 포함:**
```python
logger.info("my_event", custom="value")
# 출력: {"event": "my_event", "custom": "value",
#        "request_id": "req-xxx", "user_id": 42, ...}
```

**수동으로 컨텍스트 추가 (서비스 레이어에서):**
```python
bind_context(rag_key="sample-docs", model_used="gpt-4o")
logger.info("rag_search_started", query=query)
# → request_id + user_id + rag_key + model_used 모두 포함됨
```

**실제 구현 코드:** `src/common/middleware.py`, `src/common/logging.py`
    """,
)
async def context_demo(request: Request):
    bind_context(demo_field="샘플_추가_컨텍스트")

    logger.info("context_demo_called", endpoint="observability")

    return {
        "request_id_header": request.headers.get("X-Request-ID", "없음"),
        "logging_context": get_context(),
        "note": "위의 context가 이 요청의 모든 로그에 자동 포함됩니다.",
    }


# ── 패턴 4: Prometheus 지표 수동 기록 ────────────────────────────────────────

@router.get(
    "/metrics-demo",
    summary="Prometheus 지표 수동 기록",
    description="""
커스텀 Prometheus 지표를 직접 기록하는 패턴.

**사용 가능한 지표 (src/common/metrics.py):**
| 지표 | 타입 | 레이블 | 설명 |
|------|------|--------|------|
| `http_requests_total` | Counter | method, endpoint, status | HTTP 요청 수 |
| `llm_inference_duration_seconds` | Histogram | model | LLM 응답 시간 |
| `llm_stream_duration_seconds` | Histogram | model | 스트리밍 시간 |
| `db_connections` | Gauge | — | 활성 DB 연결 수 |

**HTTP 지표는 MetricsMiddleware가 자동 기록.**
LLM 호출 등 도메인 지표는 직접 기록:

```python
import time
from src.common.metrics import llm_inference_duration_seconds

start = time.monotonic()
response = await llm.ainvoke(messages)
llm_inference_duration_seconds.labels(model="gpt-4o").observe(
    time.monotonic() - start
)
```

**지표 확인:** `GET /metrics` (포트 8063, Prometheus scrape endpoint)
    """,
)
async def metrics_demo(model: str = "gpt-4o"):
    simulated_duration = random.uniform(0.1, 2.5)

    llm_inference_duration_seconds.labels(model=model).observe(simulated_duration)

    http_requests_total.labels(
        method="GET",
        endpoint="/sample/observability/metrics-demo",
        status="200",
    ).inc()

    logger.info(
        "metrics_demo_recorded",
        metric="llm_inference_duration_seconds",
        model=model,
        duration_seconds=round(simulated_duration, 3),
    )

    return {
        "recorded_metric": "llm_inference_duration_seconds",
        "model_label": model,
        "simulated_duration_seconds": round(simulated_duration, 3),
        "metrics_endpoint": "GET /metrics (port 8063)",
        "grafana_dashboard": "http://localhost:8064",
    }
