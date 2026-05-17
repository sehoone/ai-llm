import functools
import inspect
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastmcp import Context
from fastmcp.exceptions import ToolError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.config import Settings
from src.core.logging import get_logger

logger = get_logger("core.auth")

_BYPASS_PATHS = frozenset({"/auth/token", "/auth/refresh", "/health"})


# ── Token 생성 ─────────────────────────────────────────────────────────────

def create_access_token(sub: str, settings: Settings) -> str:
    return _encode(sub, "access", timedelta(minutes=settings.jwt_access_token_expire_minutes), settings)


def create_refresh_token(sub: str, settings: Settings) -> str:
    return _encode(sub, "refresh", timedelta(days=settings.jwt_refresh_token_expire_days), settings)


def _encode(sub: str, token_type: str, expire_delta: timedelta, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "type": token_type, "iat": now, "exp": now + expire_delta}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ── Token 검증 ─────────────────────────────────────────────────────────────

def decode_token(token: str, settings: Settings) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def verify_user(username: str, password: str, settings: Settings) -> bool:
    stored = settings.auth_users_dict.get(username)
    if stored is None:
        return False
    return secrets.compare_digest(stored, password)


# ── HTTP 미들웨어 ──────────────────────────────────────────────────────────

class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _BYPASS_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")

        if self.settings.auth_mode == "per-tool":
            # 토큰이 있으면 파싱해서 state에 주입, 없으면 통과 (도구가 직접 검증)
            if auth.startswith("Bearer "):
                token = auth[7:]
                try:
                    payload = decode_token(token, self.settings)
                except jwt.ExpiredSignatureError:
                    logger.warning("auth_token_expired", extra={"path": request.url.path})
                    return JSONResponse({"error": "Token expired"}, status_code=401)
                except jwt.InvalidTokenError:
                    logger.warning("auth_token_invalid", extra={"path": request.url.path})
                    return JSONResponse({"error": "Invalid token"}, status_code=401)

                if payload.get("type") == "access":
                    request.state.user = payload["sub"]
            return await call_next(request)

        # global 모드 — 토큰 없으면 즉시 차단
        if not auth.startswith("Bearer "):
            logger.warning(
                "auth_missing_token",
                extra={"path": request.url.path, "method": request.method},
            )
            return JSONResponse({"error": "Authorization header missing"}, status_code=401)

        token = auth[7:]
        try:
            payload = decode_token(token, self.settings)
        except jwt.ExpiredSignatureError:
            logger.warning("auth_token_expired", extra={"path": request.url.path})
            return JSONResponse({"error": "Token expired"}, status_code=401)
        except jwt.InvalidTokenError:
            logger.warning("auth_token_invalid", extra={"path": request.url.path})
            return JSONResponse({"error": "Invalid token"}, status_code=401)

        if payload.get("type") != "access":
            logger.warning("auth_wrong_token_type", extra={"path": request.url.path})
            return JSONResponse({"error": "Access token required"}, status_code=401)

        request.state.user = payload["sub"]
        return await call_next(request)


# ── 도구 레벨 인증 ────────────────────────────────────────────────────────────

async def require_auth(ctx: Context) -> str:
    """인증된 사용자명을 반환. 미인증이면 ToolError. stdio 등 비-HTTP transport는 스킵."""
    if ctx is None:
        raise ToolError("Authentication required")
    try:
        request = ctx.request_context.request
        user = getattr(request.state, "user", None)
    except AttributeError:
        return ""
    if user is None:
        raise ToolError("Authentication required")
    return user


def protected(fn):
    """인증이 필요한 MCP 도구에 붙이는 데코레이터.

    functools.wraps로 원본 시그니처를 유지하므로 FastMCP 도구 등록에 영향 없음.

    사용법::

        @mcp.tool()
        @tool_logger(logger)
        @protected
        async def my_tool(ctx: Context, ...) -> dict:
            ...
    """
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        bound = inspect.signature(fn).bind(*args, **kwargs)
        bound.apply_defaults()
        await require_auth(bound.arguments.get("ctx"))
        return await fn(*args, **kwargs)
    return wrapper
