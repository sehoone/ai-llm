"""인가 헬퍼 — 소유권·역할 검사 중앙화 (단계 A).

`platform`에 둔다: `User`/`UserRole`이 platform이라 core에 두면 레이어 역방향이 된다.
domains는 `domains → platform`으로 자유롭게 의존한다. 실패 시 `PermissionDeniedError`(HTTP 미의존).
"""

from __future__ import annotations

from src.core.exceptions import PermissionDeniedError
from src.platform.user.model import User, UserRole

ADMIN_ROLES: tuple[UserRole, ...] = (UserRole.ADMIN, UserRole.SUPERADMIN)


def is_admin(user: User) -> bool:
    """ADMIN 또는 SUPERADMIN인지."""
    return user.role in ADMIN_ROLES


def assert_owner_or_admin(
    user: User, owner_id: int, *, message: str = "접근 권한이 없습니다."
) -> None:
    """리소스 소유자이거나 관리자일 때만 통과. 아니면 PermissionDeniedError(403)."""
    if user.id != owner_id and user.role not in ADMIN_ROLES:
        raise PermissionDeniedError(message)
