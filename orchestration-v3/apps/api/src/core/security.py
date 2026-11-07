"""인증 — 비밀번호 해싱 + 자체 JWT(HS256) 발급/검증.

현재 체계: 백엔드가 ID/PW로 자격을 직접 검증하고 HS256 JWT를 발급한다.
비밀번호는 bcrypt로 해싱해 로컬 users 테이블에 보관한다.

아래 `verify_token`(OIDC JWKS 검증)은 보존된 비활성 코드다 — 사내 IdP(OIDC)로
복귀할 때 재사용한다(ADR-0003 참고). 현재 요청 경로에서는 사용하지 않는다.
"""

from __future__ import annotations

import datetime as dt

import bcrypt
import jwt
from jwt import PyJWKClient

from src.core.config import settings

# ── 비밀번호 해싱 (bcrypt) ──────────────────────────────────


def _pw_bytes(plain: str) -> bytes:
    """bcrypt는 72바이트까지만 반영 — 초과분은 잘라 일관되게 처리(해시·검증 동일)."""
    return plain.encode("utf-8")[:72]


def hash_password(plain: str) -> str:
    """평문 비밀번호를 bcrypt 해시로 변환(저장용)."""
    return bcrypt.hashpw(_pw_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """평문과 저장된 bcrypt 해시를 비교."""
    try:
        return bcrypt.checkpw(_pw_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── 자체 발급 JWT (HS256) ───────────────────────────────────


def create_access_token(subject: str, claims: dict | None = None) -> str:
    """로컬 사용자에 대한 access token 발급. subject는 로컬 user id."""
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict = {
        "sub": subject,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.access_token_expire_minutes),
        **(claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """자체 발급 HS256 토큰의 서명·만료를 검증하고 클레임을 반환.

    Raises:
        jwt.PyJWTError: 서명/만료 검증 실패 시.
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


# ── (비활성·보존) OIDC JWKS 검증 — IdP 복귀 시 재사용 ────────

_jwks_client: PyJWKClient | None = None


def _client() -> PyJWKClient:
    """JWKS 클라이언트 (서명 키를 내부 캐싱)."""
    global _jwks_client
    if _jwks_client is None:
        if not settings.oidc_jwks_url:
            raise RuntimeError("OIDC_JWKS_URL이 설정되지 않았습니다.")
        _jwks_client = PyJWKClient(settings.oidc_jwks_url, cache_keys=True)
    return _jwks_client


def verify_token(token: str) -> dict:
    """IdP 발급 OIDC 토큰의 서명·issuer·audience·만료를 검증하고 클레임을 반환.

    Raises:
        jwt.PyJWTError: 서명/클레임 검증 실패 시.
    """
    signing_key = _client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.oidc_audience or None,
        issuer=settings.oidc_issuer or None,
        options={"verify_aud": bool(settings.oidc_audience)},
    )
