"""ASGI 진입점 — uvicorn이 각 워커 프로세스에서 import하는 파일.

uvicorn이 workers > 1로 동작할 때 각 워커는 독립된 새 Python 프로세스로 fork된다.
이때 app 객체를 메모리에서 그대로 복사하는 게 아니라, 워커마다 직접 import해서 새로 만들어야 한다.

    uvicorn.run(app,            workers=4)  # app 객체를 직렬화할 수 없어 workers 무시됨
    uvicorn.run("src.asgi:app", workers=4)  # 각 워커가 이 파일을 import해 app을 독립적으로 초기화

따라서 app 빌드 로직(미들웨어 등록, rate limiter 연결)을 main.py에서 이 파일로 분리했다.
단일 워커(workers=1)도 동일한 경로를 통해 실행해 코드 경로를 하나로 유지한다.
"""
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette_prometheus import PrometheusMiddleware
from starlette_prometheus import metrics as prometheus_metrics

from src.app import mcp
from src.auth.setup import limiter, setup_auth
from src.core.config import get_settings
from src.core.middleware import RequestIDMiddleware

settings = get_settings()

# /metrics — JWT 인증 없이 Prometheus가 스크래핑.
@mcp.custom_route("/metrics", methods=["GET"])
async def metrics_endpoint(request: Request) -> Response:
    return prometheus_metrics(request)

_middleware = (
    setup_auth(mcp, settings)
    + [
        Middleware(PrometheusMiddleware),
        Middleware(RequestIDMiddleware),
    ]
)
app = mcp.http_app(middleware=_middleware, transport=settings.mcp_transport)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
