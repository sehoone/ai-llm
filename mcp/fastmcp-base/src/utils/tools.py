import ast
import ipaddress
import operator
from datetime import datetime, timezone
from typing import Any, Union
from urllib.parse import urlparse

import httpx
from fastmcp import Context
from fastmcp.exceptions import ToolError

from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp

logger = get_logger("utils.tools")

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node: ast.expr) -> Union[int, float]:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("지원하지 않는 수식입니다.")


def safe_eval(expression: str) -> Union[int, float]:
    tree = ast.parse(expression.strip(), mode="eval")
    return _eval_node(tree.body)


@mcp.tool()
@tool_logger(logger)
async def get_time() -> dict[str, Any]:
    """현재 시간 정보를 반환합니다 (UTC)."""
    now = datetime.now(timezone.utc)
    return {
        "current_time": now.isoformat(),
        "formatted": now.strftime("%Y년 %m월 %d일 %H시 %M분 %S초 (UTC)"),
        "day_of_week": ["월", "화", "수", "목", "금", "토", "일"][now.weekday()],
        "timestamp": now.timestamp(),
    }


@mcp.tool()
@tool_logger(logger, param_keys=["expression"])
async def calculate(expression: str) -> dict[str, Any]:
    """수식을 계산합니다. 예: '2 + 3 * 4', '(10 - 2) / 4'"""
    try:
        result = safe_eval(expression)
        return {"expression": expression, "result": result, "type": type(result).__name__}
    except (ValueError, ZeroDivisionError, SyntaxError) as e:
        raise ToolError(str(e))


def _validate_ping_url(url: str) -> None:
    """SSRF 방어: http/https scheme 강제, 사설·루프백 IP 차단."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ToolError("http 또는 https URL만 허용됩니다.")
    hostname = parsed.hostname
    if not hostname:
        raise ToolError("유효하지 않은 URL입니다.")
    _BLOCKED_HOSTS = {"localhost", "metadata.google.internal"}
    if hostname.lower() in _BLOCKED_HOSTS or hostname.endswith(".local"):
        raise ToolError("내부 호스트명은 허용되지 않습니다.")
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ToolError("사설/루프백 IP 주소는 허용되지 않습니다.")
    except ValueError:
        pass  # 도메인 이름 — IP 검사 불필요


@mcp.tool()
@tool_logger(logger, param_keys=["url"])
async def ping_server(url: str, ctx: Context) -> dict[str, Any]:
    """서버의 응답 시간을 확인합니다."""
    _validate_ping_url(url)
    client: httpx.AsyncClient = ctx.lifespan_context["http_client"]
    try:
        start = datetime.now()
        response = await client.get(url)
        elapsed_ms = round((datetime.now() - start).total_seconds() * 1000, 2)
        return {
            "url": url,
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
            "success": response.is_success,
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"연결 실패: {e}")
