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
