"""사내 IdP(OIDC) 토큰 검증 — ADR-0003.

인증 로직을 자작하지 않는다. 로그인·SSO·토큰 발급은 사내 IdP가 담당하고,
이 서버는 IdP의 JWKS로 발급 토큰의 서명·클레임만 검증한다 (apps/api와 동일 방식).
stdio transport에는 HTTP 미들웨어가 적용되지 않으므로 인증은 HTTP transport 전용이다.
"""

from __future__ import annotations

import functools
import inspect

import jwt
from fastmcp import Context
from fastmcp.exceptions import ToolError
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("core.security")

_BYPASS_PATHS = frozenset({"/health"})
_jwks_client: PyJWKClient | None = None


def _client() -> PyJWKClient:
    """JWKS 클라이언트 (서명 키를 내부 캐싱)."""
    global _jwks_client
    if _jwks_client is None:
        if not settings.oidc_jwks_url:
            raise RuntimeError("OIDC_JWKS_URL이 설정되지 않았습니다.")
        _jwks_client = PyJWKClient(settings.oidc_jwks_url, cache_keys=True)
    return _jwks_client


def verify_token(token: str) -> dict:
    """IdP 발급 OIDC 토큰의 서명·issuer·audience·만료를 검증하고 클레임을 반환.

    Raises:
        jwt.PyJWTError: 서명/클레임 검증 실패 시.
    """
    signing_key = _client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.oidc_audience or None,
        issuer=settings.oidc_issuer or None,
        options={"verify_aud": bool(settings.oidc_audience)},
    )


# ── HTTP 미들웨어 ──────────────────────────────────────────────────────────

class OIDCAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _BYPASS_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")

        if settings.auth_mode == "per-tool":
            # 토큰이 있으면 파싱해 state에 주입, 없으면 통과 (도구가 직접 검증)
            if auth.startswith("Bearer "):
                claims = self._verify_or_none(auth[7:], request)
                if isinstance(claims, JSONResponse):
                    return claims
            return await call_next(request)

        # global 모드 — 토큰 없으면 즉시 차단
        if not auth.startswith("Bearer "):
            logger.warning(
                "auth_missing_token",
                extra={"path": request.url.path, "method": request.method},
            )
            return JSONResponse({"error": "Authorization header missing"}, status_code=401)

        result = self._verify_or_none(auth[7:], request)
        if isinstance(result, JSONResponse):
            return result
        return await call_next(request)

    def _verify_or_none(self, token: str, request: Request):
        try:
            payload = verify_token(token)
        except jwt.PyJWTError as e:
            logger.warning("auth_token_invalid", extra={"path": request.url.path, "error": str(e)})
            return JSONResponse({"error": "Invalid token"}, status_code=401)
        request.state.user = payload.get(settings.oidc_username_claim) or payload.get("sub")
        request.state.claims = payload
        return payload


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
    """인증 필요 MCP 도구 데코레이터 — functools.wraps로 원본 시그니처 유지."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        bound = inspect.signature(fn).bind(*args, **kwargs)
        bound.apply_defaults()
        await require_auth(bound.arguments.get("ctx"))
        return await fn(*args, **kwargs)
    return wrapper
