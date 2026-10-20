"""JIT(Just-In-Time) 프로비저닝 — IdP 토큰 클레임으로 로컬 user를 생성/동기화 (ADR-0003).

- 최초 토큰 확인 시 로컬 users 행을 생성(idp_subject로 매핑).
- role은 IdP 클레임이 권위 → 이후 요청마다 로컬 레코드에 동기화.
- username/email은 생성 시에만 클레임에서 채우고, 이후 로컬 편집을 보존.
"""

from __future__ import annotations

from sqlmodel import Session

from src.core.config import settings
from src.domains.user.model import User, UserRole
from src.domains.user.repository import UserRepository

_VALID_ROLES = {r.value for r in UserRole}


def extract_role(claims: dict) -> UserRole:
    """토큰의 role 클레임(단일 문자열 또는 배열)에서 우리 역할로 매핑. 미매칭 시 USER."""
    raw = claims.get(settings.oidc_role_claim)
    candidates = raw if isinstance(raw, list) else [raw]
    for c in candidates:
        if isinstance(c, str) and c.upper() in _VALID_ROLES:
            return UserRole(c.upper())
    return UserRole.USER


def provision_user(session: Session, claims: dict) -> User:
    """토큰 클레임으로 로컬 user를 get-or-create하고 role을 동기화."""
    repo = UserRepository(session)
    subject = str(claims["sub"])
    role = extract_role(claims)

    user = repo.get_by_subject(subject)
    if user is None:
        user = User(
            idp_subject=subject,
            username=str(claims.get(settings.oidc_username_claim) or subject),
            email=str(claims.get(settings.oidc_email_claim) or ""),
            role=role,
        )
        return repo.save(user)

    # role은 IdP가 권위 — 변경 시 동기화
    if user.role != role:
        user.role = role
        repo.save(user)
    return user
