"""JWT 인증 라우트를 FastAPI APIRouter로 제공합니다."""

import jwt
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from sqlalchemy import text
from fastapi import Request

from src.core.auth import create_access_token, create_refresh_token, decode_token, verify_user
from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.mcp import _lifespan_context

logger = get_logger("auth.setup")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_client_ip)
auth_router = APIRouter()


class TokenRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@auth_router.get("/health", tags=["system"])
async def health(request: Request) -> JSONResponse:
    session_factory = _lifespan_context.get("db_session")
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


@auth_router.post("/auth/token", tags=["auth"])
@limiter.limit("5/1minutes")
async def issue_token(request: Request, body: TokenRequest) -> JSONResponse:
    settings = get_settings()
    if not verify_user(body.username, body.password, settings):
        logger.warning("login_failed", username=body.username)
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    logger.info("login_success", username=body.username)
    return JSONResponse(
        {
            "access_token": create_access_token(body.username, settings),
            "refresh_token": create_refresh_token(body.username, settings),
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
        }
    )


@auth_router.post("/auth/refresh", tags=["auth"])
async def refresh_token(body: RefreshRequest) -> JSONResponse:
    settings = get_settings()
    try:
        payload = decode_token(body.refresh_token, settings)
    except jwt.ExpiredSignatureError:
        logger.warning("token_refresh_failed", reason="expired")
        return JSONResponse({"error": "Refresh token expired"}, status_code=401)
    except jwt.InvalidTokenError:
        logger.warning("token_refresh_failed", reason="invalid")
        return JSONResponse({"error": "Invalid refresh token"}, status_code=401)

    if payload.get("type") != "refresh":
        return JSONResponse({"error": "Refresh token required"}, status_code=401)

    sub = payload["sub"]
    logger.info("token_refreshed", username=sub)
    return JSONResponse(
        {
            "access_token": create_access_token(sub, settings),
            "refresh_token": create_refresh_token(sub, settings),
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
        }
    )
