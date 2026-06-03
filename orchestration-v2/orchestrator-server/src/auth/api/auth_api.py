"""JWT/Keycloak 인증 의존성 모듈.

login/register/refresh 엔드포인트는 platform-server로 이관됨.
이 모듈은 orchestrator 내부 엔드포인트 보호를 위한 의존성만 제공.

AUTH_MODE=keycloak : Keycloak RS256 검증 + JIT 사용자 프로비저닝
AUTH_MODE=jwt      : 공유 비밀키 HS256 검증 (기존 방식)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from src.auth.services.api_key_service import api_key_service
from src.auth.services.auth_service import verify_token
import src.auth.services.keycloak_service as keycloak_service
from src.common.config import settings
from src.common.logging import bind_context, logger
from src.common.services.database import database_service
from src.common.services.sanitization import sanitize_string
from src.user.models.user_model import User, UserRole

# 빈 라우터 — api.py와의 하위 호환성 유지
router = APIRouter()

security = HTTPBearer()


def _map_keycloak_roles(roles: list[str]) -> UserRole:
    """Keycloak realm 역할 목록을 내부 UserRole로 변환한다."""
    roles_lower = [r.lower() for r in roles]
    if "superadmin" in roles_lower:
        return UserRole.SUPERADMIN
    if "admin" in roles_lower:
        return UserRole.ADMIN
    return UserRole.USER


async def _resolve_keycloak_user(token: str) -> User:
    """Keycloak JWT를 검증하고 사용자를 반환한다.

    사용자가 로컬 DB에 없으면 JIT(Just-In-Time) 프로비저닝으로 생성한다.
    이미 존재하지만 keycloak_id가 없는 경우 이메일로 매칭 후 keycloak_id를 연결한다.

    Raises:
        HTTPException 401: 토큰이 유효하지 않을 때.
        HTTPException 403: 계정이 비활성화됐을 때.
    """
    payload = await keycloak_service.verify_keycloak_token(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid Keycloak token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    keycloak_id: str = payload.get("sub", "")
    email: str = payload.get("email", "")
    preferred_username: str = payload.get("preferred_username", "")
    realm_roles: list[str] = payload.get("realm_access", {}).get("roles", [])
    role = _map_keycloak_roles(realm_roles)

    # 1. keycloak_id로 조회
    user = await database_service.get_user_by_keycloak_id(keycloak_id)

    # 2. 없으면 이메일로 조회 → keycloak_id 연결
    if user is None and email:
        user = await database_service.get_user_by_email(email)
        if user is not None:
            await database_service.update_user_keycloak_id(user.id, keycloak_id)

    # 3. 그래도 없으면 JIT 프로비저닝
    if user is None:
        user = await database_service.create_keycloak_user(
            keycloak_id=keycloak_id,
            email=email,
            username=preferred_username or email.split("@")[0],
            role=role,
        )

    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is inactive")

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(database_service.get_db_session),
) -> User:
    """현재 요청의 인증 토큰을 검증하고 사용자를 반환한다.

    인증 우선순위:
    1. API 키 (sk- 접두사) — AUTH_MODE 무관하게 항상 지원
    2. Keycloak RS256 JWT (AUTH_MODE=keycloak)
    3. HS256 JWT (AUTH_MODE=jwt, 기본값)
    """
    try:
        token = sanitize_string(credentials.credentials)

        # API 키는 AUTH_MODE와 무관하게 처리
        if token.startswith("sk-"):
            api_key = api_key_service.get_api_key_by_token(session, token)
            if not api_key:
                raise HTTPException(status_code=401, detail="Invalid API Key")
            user = await database_service.get_user(api_key.user_id)
            if not user:
                raise HTTPException(status_code=401, detail="User for API key not found")
            bind_context(user_id=user.id)
            return user

        # Keycloak 모드
        if settings.AUTH_MODE == "keycloak":
            user = await _resolve_keycloak_user(token)
            bind_context(user_id=user.id)
            return user

        # HS256 JWT 모드 (기존)
        payload = verify_token(token)
        if payload is None:
            logger.error("invalid_token_payload", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if token_type == "api_key":
            api_key = api_key_service.get_api_key_by_token(session, token)
            if not api_key:
                logger.warning("api_key_revoked_or_not_found", user_id=user_id)
                raise HTTPException(status_code=401, detail="API Key is invalid or revoked")

        user_id_int = int(user_id)
        user = await database_service.get_user(user_id_int)
        if user is None:
            logger.error("user_not_found", user_id=user_id_int)
            raise HTTPException(
                status_code=404,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        bind_context(user_id=user_id_int)
        return user

    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """ADMIN 또는 SUPERADMIN 권한을 요구하는 의존성."""
    if user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        logger.warning("admin_access_denied", user_id=user.id, role=user.role)
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
