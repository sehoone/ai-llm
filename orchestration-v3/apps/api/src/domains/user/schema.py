from datetime import datetime

from pydantic import BaseModel, Field

from src.domains.user.model import UserRole


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """본인 프로필 수정. role/status는 수정 불가 (role은 IdP 권위)."""

    username: str | None = Field(default=None, min_length=2, max_length=50)
    email: str | None = None


class AdminUserUpdateRequest(BaseModel):
    """관리자 수정. 비밀번호·role 변경 없음 (IdP 소유)."""

    username: str | None = Field(default=None, min_length=2, max_length=50)
    email: str | None = None
    status: str | None = None
