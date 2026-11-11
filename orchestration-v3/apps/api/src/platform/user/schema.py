from datetime import datetime

from pydantic import BaseModel, Field

from src.platform.user.model import UserRole


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    """관리자 계정 생성. 자체 ID/PW 인증 — 초기 비밀번호를 함께 설정."""

    username: str = Field(min_length=2, max_length=50)
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER


class UserUpdateRequest(BaseModel):
    """본인 프로필 수정. role/status는 수정 불가 (role은 IdP 권위)."""

    username: str | None = Field(default=None, min_length=2, max_length=50)
    email: str | None = None


class AdminUserUpdateRequest(BaseModel):
    """관리자 프로필 수정. 비밀번호 변경은 별도 엔드포인트(본인), role 변경은 미지원."""

    username: str | None = Field(default=None, min_length=2, max_length=50)
    email: str | None = None
    status: str | None = None
