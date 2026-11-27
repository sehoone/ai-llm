"""공통 응답 래퍼. V2 platform-server의 ApiResponse<T> 계약을 계승 (프론트 호환)."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str | None = None
    data: T | None = None

    @classmethod
    def ok(cls, data: T | None = None, message: str | None = None) -> "ApiResponse[T]":
        return cls(success=True, data=data, message=message)

    @classmethod
    def fail(cls, message: str, data: T | None = None) -> "ApiResponse[T]":
        """실패 응답 — 전역 예외 핸들러(core/errors)가 사용 (ADR-0032)."""
        return cls(success=False, data=data, message=message)
