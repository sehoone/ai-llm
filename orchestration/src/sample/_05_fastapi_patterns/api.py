"""샘플 05 — FastAPI 패턴 API

Routes:
    POST /api/v1/sample/patterns/stream/basic       — 기본 SSE 스트리밍 패턴
    POST /api/v1/sample/patterns/stream/sectioned   — 섹션 헤더 포함 스트리밍
    GET  /api/v1/sample/patterns/rate-limit-test    — 레이트 리밋 테스트 (5/min)
    GET  /api/v1/sample/patterns/middleware-info    — 미들웨어 체인 정보 조회

학습 포인트:
    1. StreamingResponse + AsyncGenerator → SSE text/event-stream
    2. "data: <내용>\n\n" 포맷 (빈 줄 2개가 SSE 이벤트 구분자)
    3. "event: <type>\ndata: <내용>\n\n" 으로 이벤트 타입 지정 가능
    4. slowapi @limiter.limit() 으로 엔드포인트별 Rate Limit 설정
    5. Request-ID, Logging, Metrics 미들웨어 체인 동작 확인
"""

import asyncio
import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.chatbot.api.chatbot_api import agent
from src.chatbot.schemas.chat_schema import Message
from src.common.limiter import limiter
from src.common.config import settings

router = APIRouter()


# ── 스키마 ──────────────────────────────────────────────────────────────────────

class StreamDemoRequest(BaseModel):
    message: str
    delay_ms: int = 50
    session_id: Optional[str] = None


# ── SSE 헬퍼 (학습용 — 이 함수 자체가 핵심 패턴) ─────────────────────────────

def sse(data: str, event_type: Optional[str] = None) -> str:
    """SSE 이벤트 문자열 생성.

    SSE 프로토콜 규칙:
    - 각 필드는 "필드명: 값\\n" 형식
    - 이벤트는 빈 줄(\\n)로 종료
    - 줄바꿈 문자는 "data:" 라인을 여러 개로 분리 가능하나 복잡해지므로 이스케이프 권장
    """
    lines = []
    if event_type:
        lines.append(f"event: {event_type}")
    lines.append(f"data: {data.replace(chr(10), chr(92) + 'n')}")
    lines.append("")
    return "\n".join(lines) + "\n"


# ── 엔드포인트 ──────────────────────────────────────────────────────────────────

@router.post(
    "/stream/basic",
    summary="기본 SSE 스트리밍",
    description="""
LangGraphAgent의 스트리밍 응답을 SSE로 전달하는 패턴.

**SSE 이벤트 구조:**
```
data: {"session_id": "...", "status": "started"}

data: 안녕

data: 하세요

event: done
data: {"status": "completed"}
```

**클라이언트 수신 코드:**
```javascript
const res = await fetch('/api/v1/sample/patterns/stream/basic', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({message: '안녕하세요'})
});
for await (const chunk of streamLines(res.body)) {
  if (chunk.startsWith('data: ')) console.log(chunk.slice(6));
}
```

**실제 구현 코드:** `src/chatbot/api/chatbot_api.py` (chat/stream 엔드포인트)
    """,
)
async def stream_basic(body: StreamDemoRequest):
    session_id = body.session_id or str(uuid.uuid4())
    messages = [Message(role="user", content=body.message)]

    async def generate():
        yield sse(json.dumps({"session_id": session_id, "status": "started"}))

        try:
            async for token in agent.get_stream_response(
                messages=messages,
                session_id=session_id,
            ):
                if token:
                    yield sse(token)

            yield sse(json.dumps({"status": "completed"}), event_type="done")

        except Exception as e:
            yield sse(json.dumps({"error": str(e), "status": "error"}), event_type="error")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/stream/sectioned",
    summary="섹션 헤더 포함 스트리밍",
    description="""
딥씽킹 모드에서 think/verify/chat 노드별 섹션 이벤트를 분리하는 패턴.

**SSE 이벤트 구조:**
```
event: section
data: {"section": "analysis", "label": "분석 중..."}

data: 전략을 수립합니다...

event: section
data: {"section": "answer", "label": "답변"}

data: 최종 답변입니다...

event: done
data: {"status": "completed"}
```

**프론트엔드 활용:**
- `event: section` → 섹션 헤더 UI 렌더링
- `data:` → 현재 섹션에 텍스트 append
    """,
)
async def stream_sectioned(body: StreamDemoRequest):
    session_id = body.session_id or str(uuid.uuid4())
    messages = [Message(role="user", content=body.message)]

    SECTION_MAP = {
        "[Deep Thinking - Analysis]": ("analysis", "분석 중..."),
        "[Deep Thinking - Verification": ("verification", "검증 중..."),
        "[Deep Thinking - Answer]": ("answer", "답변"),
    }

    async def generate():
        yield sse(json.dumps({"session_id": session_id}))

        async for token in agent.get_stream_response(
            messages=messages,
            session_id=session_id,
            is_deep_thinking=True,
        ):
            if not token:
                continue

            matched = None
            for tag, (section, label) in SECTION_MAP.items():
                if tag in token:
                    matched = (section, label)
                    break

            if matched:
                yield sse(
                    json.dumps({"section": matched[0], "label": matched[1]}),
                    event_type="section",
                )
            else:
                yield sse(token)

        yield sse(json.dumps({"status": "completed"}), event_type="done")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/rate-limit-test",
    summary="레이트 리밋 테스트 (5/min)",
    description="""
엔드포인트별 Rate Limit 동작을 테스트합니다.

이 엔드포인트는 **분당 5회** 요청 제한이 설정되어 있습니다.
6번째 요청부터 **HTTP 429 Too Many Requests** 응답을 반환합니다.

**실제 설정 위치:** `src/common/config.py` `RATE_LIMIT_ENDPOINTS`
**적용 방식:** `@limiter.limit("5/minute")` 데코레이터

**slowapi 레이트 리밋 키:** 기본값은 클라이언트 IP 주소 기반
    """,
)
@limiter.limit("5/minute")
async def rate_limit_test(request: Request):
    return {
        "message": "요청 성공",
        "limit": "5/minute",
        "tip": "6번째 요청부터 HTTP 429가 반환됩니다.",
        "request_id": request.headers.get("X-Request-ID"),
        "timestamp": time.time(),
    }


@router.get(
    "/middleware-info",
    summary="미들웨어 체인 정보",
    description="""
요청에 미들웨어가 주입한 정보를 확인합니다.

**미들웨어 체인 (실행 순서):**
1. `RequestIDMiddleware` → `X-Request-ID` 헤더 주입
2. `LoggingContextMiddleware` → structlog 컨텍스트 변수 설정
3. `MetricsMiddleware` → Prometheus 지표 측정
4. `CORSMiddleware` → CORS 헤더 추가

**실제 구현 코드:** `src/common/middleware.py`
    """,
)
async def middleware_info(request: Request):
    return {
        "request_id": request.headers.get("X-Request-ID", "없음 (RequestIDMiddleware가 주입함)"),
        "client_ip": request.client.host if request.client else "unknown",
        "method": request.method,
        "path": request.url.path,
        "headers": {
            k: v for k, v in request.headers.items()
            if k.lower() not in ("authorization", "cookie")
        },
        "middleware_chain": [
            "RequestIDMiddleware (X-Request-ID 헤더 주입)",
            "LoggingContextMiddleware (structlog 컨텍스트)",
            "MetricsMiddleware (Prometheus 지표)",
            "CORSMiddleware (CORS 헤더)",
        ],
    }
