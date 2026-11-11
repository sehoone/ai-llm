"""도메인 예외 — 서비스 레이어가 HTTP를 모른 채 실패를 표현한다 (단계 A).

서비스/엔진은 이 예외를 raise하고, `main.py`의 전역 핸들러가 `ApiResponse(success=False)` +
적절한 상태코드로 변환한다. 서비스가 `fastapi.HTTPException`을 직접 다루지 않으므로(ADR-0005 경계),
워크플로우 노드·배치 등 HTTP 밖에서도 동일 로직을 재사용할 수 있다.
"""

from __future__ import annotations


class DomainError(Exception):
    """도메인 레이어 기본 예외. 기본 400. 하위 클래스가 status_code를 재정의."""

    status_code: int = 400

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ValidationError(DomainError):
    """입력이 유효하지 않음 (400)."""

    status_code = 400


class UnauthorizedError(DomainError):
    """인증 필요/실패 (401)."""

    status_code = 401


class PermissionDeniedError(DomainError):
    """인증은 됐으나 권한 없음 (403)."""

    status_code = 403


class NotFoundError(DomainError):
    """리소스 없음 (404)."""

    status_code = 404


class ConflictError(DomainError):
    """상태 충돌 — 중복·전이 불가 등 (409)."""

    status_code = 409
