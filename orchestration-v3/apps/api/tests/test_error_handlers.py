"""전역 예외 핸들러 정규화 테스트 (ADR-0032).

모든 에러 응답이 ApiResponse(success=False) + request_id 형태인지 검증한다.
404·422는 실제 앱에서(DB 불필요), 500(catch-all)은 throwaway 앱에 핸들러를 붙여 확인한다.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.errors import register_exception_handlers
from src.main import app

client = TestClient(app)


def _assert_normalized(body: dict) -> None:
    assert body["success"] is False
    assert isinstance(body["message"], str) and body["message"]
    assert "request_id" in body


def test_not_found_normalized() -> None:
    # 라우팅 404(starlette 원형 HTTPException)도 ApiResponse로 정규화 + X-Request-ID echo.
    res = client.get("/api/v1/does-not-exist")
    assert res.status_code == 404
    _assert_normalized(res.json())
    assert res.headers.get("x-request-id")


def test_validation_error_normalized() -> None:
    # 빈 바디 → RequestValidationError(422). DB 접근 전 단계라 연결 불필요.
    res = client.post("/api/v1/auth/login", json={})
    assert res.status_code == 422
    body = res.json()
    _assert_normalized(body)
    assert "errors" in body["data"]  # 상세는 data.errors로 보존


def test_unhandled_exception_normalized() -> None:
    # catch-all — 미처리 예외도 500 + 정규화(내부 상세 비노출).
    throwaway = FastAPI()
    register_exception_handlers(throwaway)

    @throwaway.get("/boom")
    def _boom() -> None:
        raise RuntimeError("kaboom")

    local = TestClient(throwaway, raise_server_exceptions=False)
    res = local.get("/boom")
    assert res.status_code == 500
    body = res.json()
    _assert_normalized(body)
    assert "kaboom" not in body["message"]  # 내부 메시지 미노출
