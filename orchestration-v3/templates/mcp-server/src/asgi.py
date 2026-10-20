"""ASGI 진입점 — uvicorn이 import하는 파일 (poe dev / Docker).

HTTP transport로 /mcp 엔드포인트를 노출하고, OIDC 검증·요청ID 미들웨어를 조립한다.
stdio transport는 main.py에서 mcp.run으로 실행하며 이 파일을 거치지 않는다(인증 미적용).
"""
from sqlalchemy import text
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.app import mcp
from src.core.config import settings
from src.core.mcp import get_lifespan_context
from src.core.middleware import RequestIDMiddleware
from src.core.security import OIDCAuthMiddleware


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


_middleware = [
    Middleware(OIDCAuthMiddleware),
    Middleware(RequestIDMiddleware),
]
app = mcp.http_app(middleware=_middleware, transport=settings.mcp_transport)
