import secrets
from datetime import datetime, timedelta, timezone

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.config import Settings

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
        if not auth.startswith("Bearer "):
            return JSONResponse({"error": "Authorization header missing"}, status_code=401)

        token = auth[7:]
        try:
            payload = decode_token(token, self.settings)
        except jwt.ExpiredSignatureError:
            return JSONResponse({"error": "Token expired"}, status_code=401)
        except jwt.InvalidTokenError:
            return JSONResponse({"error": "Invalid token"}, status_code=401)

        if payload.get("type") != "access":
            return JSONResponse({"error": "Access token required"}, status_code=401)

        request.state.user = payload["sub"]
        return await call_next(request)
