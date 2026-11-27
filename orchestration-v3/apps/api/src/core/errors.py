"""전역 예외 핸들러 — 모든 에러 응답을 ApiResponse(success=False)로 정규화 (ADR-0032).

배경: admin/portal의 axios 인터셉터는 `{success, data}` 래퍼를 전제로 unwrap한다(ADR-0006).
그런데 FastAPI 기본 에러 응답은 `{"detail": ...}`라 래퍼 계약을 위반했다. 미처리 예외(500)도
스택만 로깅되고 응답 포맷이 제각각이었다. 여기서 세 부류를 한 포맷으로 묶는다:

  - HTTPException        → 그 status_code 유지 + detail을 message로
  - RequestValidationError → 422 + 첫 검증 오류를 message로(상세는 data.errors)
  - 그 외 Exception      → 500 + 고정 메시지(내부 상세 비노출) + logger.exception

응답 바디에 `request_id`(contextvar, ADR-0031)를 실어 로그↔응답을 상관시킨다.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# HTTPException은 starlette 베이스로 import·등록한다 — fastapi.HTTPException(서브클래스)과
# 라우팅 404/405(starlette 원형)를 MRO로 함께 포착하기 위함.
from starlette.exceptions import HTTPException

from src.core.logging import request_id_var
from src.core.response import ApiResponse

logger = logging.getLogger("src.errors")


def _payload(message: str, data: object | None = None) -> dict:
    body = ApiResponse.fail(message=message, data=data).model_dump()
    body["request_id"] = request_id_var.get()
    return body


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # 인증/인가/404 등 의도된 HTTP 에러 — detail을 message로 옮기고 상태코드·헤더는 보존.
    message = exc.detail if isinstance(exc.detail, str) else "요청을 처리할 수 없습니다."
    return JSONResponse(status_code=exc.status_code, content=_payload(message), headers=exc.headers)


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # 요청 검증 실패 — 첫 오류를 사람이 읽을 message로, 전체는 data.errors로.
    errors = exc.errors()
    first = errors[0] if errors else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    detail = first.get("msg", "유효하지 않은 요청입니다.")
    message = f"{loc}: {detail}" if loc else "유효하지 않은 요청입니다."
    return JSONResponse(status_code=422, content=_payload(message, data={"errors": errors}))


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 미처리 예외 — 스택을 남기되 내부 상세는 클라이언트에 노출하지 않는다(request_id로 추적).
    logger.exception("unhandled_exception path=%s", request.url.path)
    return JSONResponse(status_code=500, content=_payload("서버 내부 오류가 발생했습니다."))


def register_exception_handlers(app: FastAPI) -> None:
    """main.py에서 1회 호출 — 세 부류 핸들러를 등록한다."""
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
