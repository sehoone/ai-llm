"""사내 IdP(OIDC) 토큰 검증.

인증 로직을 자작하지 않는다 — 로그인·SSO·SAML·LDAP는 사내 IdP가 담당하고,
백엔드는 IdP의 JWKS로 발급 토큰의 서명·클레임만 검증한다 (ADR-0003).
"""

from __future__ import annotations

import jwt
from jwt import PyJWKClient

from src.core.config import settings

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
