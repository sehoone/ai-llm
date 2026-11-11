"""인증 서비스 — ID/PW 자격 검증 + seed 관리자 보장.

백엔드가 비밀번호를 직접 검증하고 JWT를 발급한다(ADR-0003 전환). 아래 OIDC JIT
프로비저닝(`extract_role`·`provision_user`)은 보존된 비활성 코드 — IdP 복귀 시 재사용.
"""

from __future__ import annotations

import logging

from sqlmodel import Session

from src.core.config import settings
from src.core.security import hash_password, verify_password
from src.platform.user.model import User, UserRole
from src.platform.user.repository import UserRepository

logger = logging.getLogger(__name__)

_VALID_ROLES = {r.value for r in UserRole}


def authenticate(session: Session, username: str, password: str) -> User | None:
    """username + 비밀번호로 사용자를 검증. 실패 시 None.

    (타이밍 공격 완화를 위해 사용자 부재 시에도 해시 비교를 수행.)
    """
    user = UserRepository(session).get_by_username(username)
    hashed = user.hashed_password if user and user.hashed_password else _DUMMY_HASH
    ok = verify_password(password, hashed)
    if not ok or user is None or not user.hashed_password:
        return None
    if user.status != "active":
        return None
    return user


# 사용자 부재 시 비교용 더미 해시(타이밍 균일화). 모듈 로드 1회 계산.
_DUMMY_HASH = hash_password("x")


def ensure_seed_admin(session: Session) -> None:
    """최초 로그인용 seed SUPERADMIN을 보장. 비밀번호 미설정 시 건너뜀."""
    if not settings.seed_admin_password:
        return
    repo = UserRepository(session)
    if repo.get_by_username(settings.seed_admin_username) is not None:
        return
    user = User(
        username=settings.seed_admin_username,
        email=settings.seed_admin_email,
        hashed_password=hash_password(settings.seed_admin_password),
        role=UserRole.SUPERADMIN,
    )
    repo.save(user)
    logger.info("seed 관리자 생성: %s", settings.seed_admin_username)


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
