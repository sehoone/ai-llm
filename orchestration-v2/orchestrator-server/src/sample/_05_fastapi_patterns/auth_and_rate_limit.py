"""샘플 05: FastAPI 인증 + 레이트 리밋 패턴

실제 구현:
- 인증: src/auth/services/auth_service.py, src/auth/api/auth_api.py
- 세션 소유권: src/chatbot/deps.py
- 레이트 리밋: src/common/limiter.py, src/main.py

핵심 개념:
- JWT 인증: Bearer 토큰으로 모든 보호된 엔드포인트 접근
- Depends 체인: 인증 → 사용자 조회 → 소유권 검증을 함수 체인으로 구성
- 소유권 검증: 사용자가 자신의 리소스만 접근 가능
- slowapi 레이트 리밋: 엔드포인트별 다른 제한 적용
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ── JWT 설정 ──────────────────────────────────────────────────────────────────

JWT_SECRET = "your-secret-key-here"  # 실제: settings.JWT_SECRET_KEY
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ── 레이트 리밋 설정 ──────────────────────────────────────────────────────────

# key_func: 어떤 기준으로 제한할지 결정
# get_remote_address: IP 주소 기준 (실제 코드에서는 인증된 user_id 기준도 가능)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Auth & Rate Limit Patterns")
app.state.limiter = limiter


# slowapi 예외 핸들러: 제한 초과 시 429 응답
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"요청이 너무 많습니다. 잠시 후 다시 시도하세요."},
    )


# ── 스키마 ──────────────────────────────────────────────────────────────────────

class UserInDB(BaseModel):
    """DB에 저장된 사용자 모델 (단순화)."""
    id: str
    email: str
    is_admin: bool = False


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── JWT 유틸리티 ──────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """토큰 디코딩 + 검증. 실패 시 예외 발생."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── 의존성 함수 체인 ──────────────────────────────────────────────────────────

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserInDB:
    """Authorization 헤더에서 JWT를 추출하고 사용자를 반환.

    Depends(security): "Authorization: Bearer <token>" 헤더를 자동으로 파싱
    """
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="액세스 토큰이 필요합니다.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    # 실제 코드: DB에서 사용자 조회 (await database_service.get_user_by_id(user_id))
    # 단순화를 위해 직접 생성
    return UserInDB(id=user_id, email=f"{user_id}@example.com")


async def get_admin_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """관리자 권한 확인.

    Depends 체인: get_current_user → get_admin_user
    인증 + 권한 검사를 분리하여 재사용성 확보
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다.",
        )
    return current_user


def get_owned_session(session_owner_id: Optional[str] = None):
    """세션 소유권 검증 의존성 팩토리.

    실제 코드 패턴 (src/chatbot/deps.py):
        async def get_owned_chat_session(
            session_id: str,
            current_user: UserInDB = Depends(get_current_user),
            session: Session = Depends(get_session),
        ) -> ChatSession:
            chat_session = await session_service.get_session(session_id)
            if chat_session.user_id != current_user.id:
                raise HTTPException(403, "이 세션에 접근할 수 없습니다.")
            return chat_session

    여기서는 개념 시연을 위해 단순화.
    """
    async def dependency(
        session_id: str,
        current_user: UserInDB = Depends(get_current_user),
    ) -> str:
        # 실제: DB에서 session 조회 후 user_id 비교
        # 세션이 사용자 것이 아니면 403 (404 대신 403 — 존재 여부 노출 방지)
        simulated_owner = session_owner_id or current_user.id
        if simulated_owner != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 세션에 접근할 수 없습니다.",
            )
        return session_id

    return dependency


# ── 엔드포인트 ──────────────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=TokenResponse)
@limiter.limit("20/minute")  # 로그인: 분당 20회 (브루트포스 방지)
async def login(request: Request, body: LoginRequest):
    """로그인 — access/refresh 토큰 발급.

    실제 코드에서는:
    1. DB에서 이메일로 사용자 조회
    2. bcrypt로 비밀번호 검증
    3. 로그인 실패 횟수 추적 (account lockout)
    """
    # 단순화: 실제로는 DB 조회 + 비밀번호 해시 검증
    if body.password != "correct-password":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    user_id = "user-123"
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@app.get("/profile")
async def get_profile(current_user: UserInDB = Depends(get_current_user)):
    """인증된 사용자의 프로필 반환 (레이트 리밋 없음)."""
    return {"user_id": current_user.id, "email": current_user.email}


@app.post("/chat/{session_id}/message")
@limiter.limit("30/minute")  # 채팅: 분당 30회
async def send_message(
    request: Request,
    session_id: str = Depends(get_owned_session()),  # 소유권 검증 포함
    current_user: UserInDB = Depends(get_current_user),
):
    """채팅 메시지 전송.

    Depends 체인:
    1. get_current_user: JWT 검증 → UserInDB 반환
    2. get_owned_session: session_id가 current_user 소유인지 확인
    """
    return {
        "session_id": session_id,
        "user_id": current_user.id,
        "message": "처리됨",
    }


@app.get("/admin/users")
@limiter.limit("10/minute")  # 관리자 API: 더 엄격한 제한
async def list_users(
    request: Request,
    admin: UserInDB = Depends(get_admin_user),  # 관리자만 접근
):
    """전체 사용자 목록 (관리자 전용)."""
    return {"users": [], "requested_by": admin.id}


"""
사용 예시:

# 로그인
curl -X POST "http://localhost:8000/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"email": "user@example.com", "password": "correct-password"}'

# 인증된 요청
curl "http://localhost:8000/profile" \\
  -H "Authorization: Bearer <access_token>"

# 채팅 (세션 소유권 검증 포함)
curl -X POST "http://localhost:8000/chat/session-001/message" \\
  -H "Authorization: Bearer <access_token>"
"""
