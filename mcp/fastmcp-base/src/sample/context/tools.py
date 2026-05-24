"""[케이스 04 - context] MCP Context 활용 패턴

다루는 패턴:
  1. ctx.info / ctx.warning / ctx.error — 클라이언트에 실시간 로그 전송
  2. ctx.report_progress(current, total) — 진행률 보고 (긴 작업)
  3. ctx.lifespan_context — lifespan에서 초기화한 공유 객체 접근
  4. ctx.request_context — HTTP 요청 정보 접근 (transport별 주의사항)

Context vs logger 차이:
  - logger.info() → 서버 콘솔/파일 로그 (운영자용)
  - ctx.info()    → MCP 클라이언트로 전송되는 로그 메시지 (AI/사용자용)

app.py 등록:
    from src.sample.context import tools as ctx_sample_tools  # noqa: F401
"""
import asyncio
from typing import Any

from fastmcp import Context
from fastmcp.exceptions import ToolError

from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp

logger = get_logger("sample.context")


# ── Tool 1: 클라이언트 로그 전송 ──────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=["msg"])  # "message"는 logging 예약어 — 사용 금지
async def ctx_send_log(message: str, ctx: Context) -> dict[str, Any]:
    """ctx.info/warning/error 로 클라이언트에 로그 전송.

    Args:
        message: 전송할 로그 메시지
        ctx: MCP 컨텍스트 (자동 주입)
    """
    await ctx.info(f"[INFO] 작업 시작: {message}")

    if "경고" in message or "warn" in message.lower():
        await ctx.warning(f"[WARNING] 주의 필요: {message}")
        level = "warning"
    elif "오류" in message or "error" in message.lower():
        await ctx.error(f"[ERROR] 오류 감지: {message}")
        level = "error"
    else:
        level = "info"

    await ctx.info("[INFO] 작업 완료")
    return {"sent": True, "level": level, "message": message}


# ── Tool 2: 진행률 보고 (긴 작업 시뮬레이션) ─────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=["item_count"])
async def ctx_batch_process(item_count: int, ctx: Context) -> dict[str, Any]:
    """배치 처리 진행률을 ctx.report_progress 로 보고.

    Args:
        item_count: 처리할 항목 수 (1~50)
        ctx: MCP 컨텍스트 (자동 주입)
    """
    item_count = max(1, min(item_count, 50))

    await ctx.info(f"배치 처리 시작: {item_count}개 항목")

    processed = 0
    failed = 0

    for i in range(item_count):
        await ctx.report_progress(i, item_count)

        await asyncio.sleep(0)  # 실제 I/O 작업 자리
        if i % 7 == 6:  # 7번째마다 실패 시뮬레이션
            failed += 1
            await ctx.warning(f"항목 {i+1} 처리 실패 (재시도 필요)")
        else:
            processed += 1

    await ctx.report_progress(item_count, item_count)
    await ctx.info(f"배치 처리 완료: 성공 {processed}개, 실패 {failed}개")

    return {
        "total": item_count,
        "processed": processed,
        "failed": failed,
        "success_rate": round(processed / item_count * 100, 1),
    }


# ── Tool 3: lifespan_context 접근 ─────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=[])
async def ctx_check_lifespan(ctx: Context) -> dict[str, Any]:
    """lifespan_context 에서 공유 객체 접근 예시."""
    lifespan_keys = list(ctx.lifespan_context.keys()) if ctx.lifespan_context else []

    db_available = "db_session" in (ctx.lifespan_context or {})

    await ctx.info(f"lifespan_context 키: {lifespan_keys}")

    return {
        "lifespan_keys": lifespan_keys,
        "db_session_available": db_available,
    }


# ── Tool 4: request_context (HTTP transport 전용) ─────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=[])
async def ctx_get_request_info(ctx: Context) -> dict[str, Any]:
    """HTTP request 정보를 ctx.request_context 에서 읽기.

    주의: streamable-http transport 에서만 동작.
          stdio transport 에서는 request_context 가 None 일 수 있음.
    """
    result: dict[str, Any] = {"transport": "unknown"}

    try:
        request = ctx.request_context.request  # type: ignore[union-attr]
        result.update({
            "transport": "http",
            "method": request.method,
            "path": str(request.url.path),
            # 인증된 경우 middleware가 request.state.user 를 설정
            "user": getattr(request.state, "user", "anonymous"),
            "client_ip": request.client.host if request.client else "unknown",
        })
    except AttributeError:
        result["transport"] = "stdio (request_context 없음)"

    return result
