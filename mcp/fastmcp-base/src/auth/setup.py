"""JWT 인증 라우트 + 미들웨어를 MCP 서버에 등록합니다."""

import jwt
from slowapi import Limiter
from sqlalchemy import text
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.auth import (
    JWTAuthMiddleware,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_user,
)
from src.core.config import Settings
from src.core.logging import get_logger
from src.core.mcp import get_lifespan_context

logger = get_logger("auth.setup")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_client_ip)


def setup_auth(mcp, settings: Settings) -> list[Middleware]:
    """auth 라우트를 mcp에 등록하고 JWT 미들웨어 목록을 반환합니다."""

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        session_factory = get_lifespan_context().get("db_session")
        db_ok: bool | None = None
        if session_factory is not None:
            try:
                async with session_factory() as db:
                    await db.execute(text("SELECT 1"))
                db_ok = True
            except Exception:
                db_ok = False
        is_ok = db_ok is not False
        return JSONResponse(
            {"status": "ok" if is_ok else "degraded", "db": db_ok},
            status_code=200 if is_ok else 503,
        )

    @mcp.custom_route("/auth/token", methods=["POST"])
    @limiter.limit("5/1minutes")
    async def issue_token(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

        username = body.get("username", "")
        password = body.get("password", "")

        if not verify_user(username, password, settings):
            logger.warning("login_failed", extra={"username": username})
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)

        logger.info("login_success", extra={"username": username})
        return JSONResponse(
            {
                "access_token": create_access_token(username, settings),
                "refresh_token": create_refresh_token(username, settings),
                "token_type": "bearer",
                "expires_in": settings.jwt_access_token_expire_minutes * 60,
            }
        )

    @mcp.custom_route("/auth/refresh", methods=["POST"])
    async def refresh_token(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

        token = body.get("refresh_token", "")
        try:
            payload = decode_token(token, settings)
        except jwt.ExpiredSignatureError:
            logger.warning("token_refresh_failed", extra={"reason": "expired"})
            return JSONResponse({"error": "Refresh token expired"}, status_code=401)
        except jwt.InvalidTokenError:
            logger.warning("token_refresh_failed", extra={"reason": "invalid"})
            return JSONResponse({"error": "Invalid refresh token"}, status_code=401)

        if payload.get("type") != "refresh":
            return JSONResponse({"error": "Refresh token required"}, status_code=401)

        sub = payload["sub"]
        logger.info("token_refreshed", extra={"username": sub})
        return JSONResponse(
            {
                "access_token": create_access_token(sub, settings),
                "refresh_token": create_refresh_token(sub, settings),
                "token_type": "bearer",
                "expires_in": settings.jwt_access_token_expire_minutes * 60,
            }
        )

    return [Middleware(JWTAuthMiddleware, settings=settings)]
