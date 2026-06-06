"""인증 의존성 모듈.

login/register/refresh 엔드포인트는 platform-server가 소유.
이 모듈은 orchestrator 내부 엔드포인트 보호를 위한 FastAPI 의존성만 제공.

인증 우선순위:
  1. API 키 (sk- 접두사)
  2. JWT HS256 (platform-server 발급, JWT_SECRET_KEY 공유)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from src.auth.services.api_key_service import api_key_service
from src.auth.services.auth_service import verify_token
from src.common.logging import bind_context, logger
from src.common.services.database import database_service
from src.common.services.sanitization import sanitize_string
from src.user.models.user_model import User, UserRole

router = APIRouter()

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(database_service.get_db_session),
) -> User:
    """현재 요청의 인증 토큰을 검증하고 사용자를 반환한다."""
    try:
        token = sanitize_string(credentials.credentials)

        if token.startswith("sk-"):
            api_key = api_key_service.get_api_key_by_token(session, token)
            if not api_key:
                raise HTTPException(status_code=401, detail="Invalid API Key")
            user = await database_service.get_user(api_key.user_id)
            if not user:
                raise HTTPException(status_code=401, detail="User for API key not found")
            bind_context(user_id=user.id)
            return user

        payload = verify_token(token)
        if payload is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = int(payload["sub"])
        user = await database_service.get_user(user_id)
        if user is None:
            logger.error("user_not_found", user_id=user_id)
            raise HTTPException(status_code=404, detail="User not found")

        bind_context(user_id=user_id)
        return user

    except HTTPException:
        raise
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve))
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
