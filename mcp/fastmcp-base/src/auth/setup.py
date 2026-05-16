"""JWT 인증 라우트 + 미들웨어를 MCP 서버에 등록합니다."""

import jwt
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


def setup_auth(mcp, settings: Settings) -> list[Middleware]:
    """auth 라우트를 mcp에 등록하고 JWT 미들웨어 목록을 반환합니다."""

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @mcp.custom_route("/auth/token", methods=["POST"])
    async def issue_token(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

        username = body.get("username", "")
        password = body.get("password", "")

        if not verify_user(username, password, settings):
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)

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
            return JSONResponse({"error": "Refresh token expired"}, status_code=401)
        except jwt.InvalidTokenError:
            return JSONResponse({"error": "Invalid refresh token"}, status_code=401)

        if payload.get("type") != "refresh":
            return JSONResponse({"error": "Refresh token required"}, status_code=401)

        sub = payload["sub"]
        return JSONResponse(
            {
                "access_token": create_access_token(sub, settings),
                "refresh_token": create_refresh_token(sub, settings),
                "token_type": "bearer",
                "expires_in": settings.jwt_access_token_expire_minutes * 60,
            }
        )

    return [Middleware(JWTAuthMiddleware, settings=settings)]
