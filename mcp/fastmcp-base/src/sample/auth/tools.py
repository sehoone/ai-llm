"""[케이스 05 - auth] 인증 패턴 샘플

다루는 패턴:
  1. @protected 데코레이터 — 모든 호출에 인증 강제
  2. require_auth(ctx) 직접 호출 — 사용자명 추출
  3. 선택적 인증 — 인증 여부에 따라 다른 데이터 반환
  4. 관리자 권한 — 특정 사용자만 허용

인증 흐름:
  클라이언트 → POST /auth/token (username/password)
             ← { access_token, refresh_token }
  클라이언트 → MCP 요청 + Authorization: Bearer <access_token>
  미들웨어   → JWT 검증 → request.state.user = "username"
  require_auth(ctx) → request.state.user 반환

설정:
  auth_mode = "per-tool"  # .env 파일에서 설정
  auth_users = "admin:admin123,user1:pass1"

app.py 등록:
    from src.sample.auth import tools as auth_sample_tools  # noqa: F401
"""
from typing import Any

from fastmcp import Context
from fastmcp.exceptions import ToolError

from src.core.auth import protected, require_auth
from src.core.config import get_settings
from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp

logger = get_logger("sample.auth")

_ADMIN_USERS = {"admin"}


# ── Tool 1: @protected — 단순 인증 강제 ──────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=[])
@protected
async def auth_get_my_profile(ctx: Context) -> dict[str, Any]:
    """현재 인증된 사용자 프로필 반환."""
    username = await require_auth(ctx)
    settings = get_settings()

    users = settings.auth_users_dict
    is_admin = username in _ADMIN_USERS

    return {
        "username": username,
        "is_admin": is_admin,
        "available_tools": ["admin_*"] if is_admin else ["user_*"],
    }


# ── Tool 2: 관리자 전용 도구 ──────────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=[])
@protected
async def auth_admin_only(ctx: Context) -> dict[str, Any]:
    """관리자만 호출 가능한 도구 예시."""
    username = await require_auth(ctx)

    if username not in _ADMIN_USERS:
        raise ToolError(f"관리자 권한이 필요합니다. 현재 사용자: {username}")

    settings = get_settings()
    return {
        "message": f"관리자 '{username}'님 환영합니다.",
        "registered_users": list(settings.auth_users_dict.keys()),
        "admin_count": len(_ADMIN_USERS),
    }


# ── Tool 3: 선택적 인증 — 인증 여부에 따라 다른 응답 ────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=[])
async def auth_optional(ctx: Context) -> dict[str, Any]:
    """인증 여부에 따라 반환 데이터가 달라지는 도구.

    @protected 없이 require_auth를 try/except로 처리해 선택적 인증 구현.
    """
    try:
        username = await require_auth(ctx)
        is_authenticated = True
    except ToolError:
        username = "anonymous"
        is_authenticated = False

    public_data = {
        "service": "FastMCP Sample API",
        "version": "1.0.0",
        "is_authenticated": is_authenticated,
    }

    if is_authenticated:
        public_data.update({
            "username": username,
            "is_admin": username in _ADMIN_USERS,
            "private_info": "인증된 사용자만 볼 수 있는 데이터",
        })

    return public_data


# ── Tool 4: 완전 공개 도구 (인증 불필요) ─────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=[])
async def auth_public_health() -> dict[str, Any]:
    """인증 없이 누구나 호출 가능한 공개 도구.

    auth_mode = "global" 일 때는 미들웨어가 이 도구도 차단하므로
    공개 도구는 /health 같은 별도 HTTP 엔드포인트로 노출 권장.
    """
    return {
        "status": "healthy",
        "auth_note": "이 도구는 auth_mode=per-tool 에서만 인증 없이 접근 가능합니다.",
    }
