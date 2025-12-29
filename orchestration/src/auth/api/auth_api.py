"""Authentication and authorization endpoints for the API.

This module provides endpoints for user registration, login, session management,
and token verification.
"""

import uuid
from datetime import timedelta
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from src.common.config import settings
from src.common.limiter import limiter
from src.common.logging import (
    bind_context,
    logger,
)
from src.chatbot.models.session_model import Session
from src.user.models.user_model import User
from src.auth.schemas.auth_schema import (
    RefreshTokenRequest,
    SessionResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from src.common.services.database import DatabaseService
from src.auth.services.auth_service import (
    create_access_token,
    verify_token,
)
from src.common.services.sanitization import (
    sanitize_email,
    sanitize_string,
    validate_password_strength,
)

router = APIRouter()
security = HTTPBearer()
db_service = DatabaseService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get the current user ID from the token.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        User: The user extracted from the token.

    Raises:
        HTTPException: If the token is invalid or missing.
    """
    try:
        # Sanitize token
        token = sanitize_string(credentials.credentials)

        user_id = verify_token(token)
        if user_id is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify user exists in database
        user_id_int = int(user_id)
        user = await db_service.get_user(user_id_int)
        if user is None:
            logger.error("user_not_found", user_id=user_id_int)
            raise HTTPException(
                status_code=404,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Bind user_id to logging context for all subsequent logs in this request
        bind_context(user_id=user_id_int)

        return user
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )





@router.post("/register", response_model=UserResponse, summary="사용자 등록", description="사용자 등록")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
async def register_user(request: Request, user_data: UserCreate):
    """Register a new user.

    Args:
        request: The FastAPI request object for rate limiting.
        user_data: User registration data

    Returns:
        UserResponse: The created user info
    """
    try:
        # Sanitize email
        sanitized_email = sanitize_email(user_data.email)

        # Extract and validate password
        password = user_data.password.get_secret_value()
        validate_password_strength(password)

        # Check if user exists
        if await db_service.get_user_by_email(sanitized_email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        user = await db_service.create_user(email=sanitized_email, password=User.hash_password(password))

        # Create access token
        token = create_access_token(str(user.id))

        return UserResponse(id=user.id, email=user.email, token=token)
    except ValueError as ve:
        logger.error("user_registration_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/login", response_model=TokenResponse, summary="사용자 로그인", description="사용자 로그인")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])
async def login(request: Request, user_data: UserLogin):
    """Login a user.

    Args:
        request: The FastAPI request object for rate limiting.
        username: User's email
        password: User's password
        grant_type: Must be "password"

    Returns:
        TokenResponse: Access token information

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        print(user_data)
        # Sanitize inputs
        username = sanitize_string(user_data.email)
        password = sanitize_string(user_data.password.get_secret_value())
        grant_type = sanitize_string(user_data.grant_type)

        # Verify grant type
        if grant_type != "password":
            raise HTTPException(
                status_code=400,
                detail="Unsupported grant type. Must be 'password'",
            )

        user = await db_service.get_user_by_email(username)
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(str(user.id), timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
        refresh_token = create_access_token(str(user.id), timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES))

        return TokenResponse(
            access_token=token.access_token,
            refresh_token=refresh_token.access_token,
            token_type="bearer",
            expires_at=token.expires_at,
        )
    except ValueError as ve:
        logger.error("login_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/refresh", response_model=TokenResponse, summary="토큰 갱신", description="Refresh Token을 사용하여 Access Token 갱신")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])
async def refresh_token(request: Request, token_data: RefreshTokenRequest):
    """Refresh access token.

    Args:
        request: The FastAPI request object for rate limiting.
        token_data: The refresh token data.

    Returns:
        TokenResponse: New access token information.

    Raises:
        HTTPException: If the refresh token is invalid.
    """
    try:
        # Verify refresh token
        user_id = verify_token(token_data.refresh_token)
        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify user exists
        user_id_int = int(user_id)
        user = await db_service.get_user(user_id_int)
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create new tokens
        token = create_access_token(str(user.id), timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
        refresh_token = create_access_token(str(user.id), timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES))

        return TokenResponse(
            access_token=token.access_token,
            refresh_token=refresh_token.access_token,
            token_type="bearer",
            expires_at=token.expires_at,
        )
    except ValueError as ve:
        logger.error("token_refresh_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/session", response_model=SessionResponse, summary="세션 생성", description="새로운 채팅 세션 생성")
async def create_session(user: User = Depends(get_current_user)):
    """Create a new chat session for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        SessionResponse: The session ID and name
    """
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Create session in database
        session = await db_service.create_session(session_id, user.id)

        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user.id,
            name=session.name,
        )

        return SessionResponse(session_id=session_id, name=session.name)
    except ValueError as ve:
        logger.error("session_creation_validation_failed", error=str(ve), user_id=user.id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.patch(
    "/session/{session_id}/name",
    response_model=SessionResponse,
    summary="세션 이름 업데이트",
    description="세션의 이름을 업데이트합니다.",
)
async def update_session_name(
    session_id: str, name: str = Form(...), user: User = Depends(get_current_user)
):
    """Update a session's name.

    Args:
        session_id: The ID of the session to update
        name: The new name for the session
        user: The authenticated user

    Returns:
        SessionResponse: The updated session information
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_name = sanitize_string(name)

        # Verify session exists and belongs to user
        session = await db_service.get_session(sanitized_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot modify other sessions")

        # Update the session name
        session = await db_service.update_session_name(sanitized_session_id, sanitized_name)

        return SessionResponse(session_id=sanitized_session_id, name=session.name)
    except ValueError as ve:
        logger.error("session_update_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.delete("/session/{session_id}", summary="세션 삭제", description="인증된 사용자의 세션을 삭제합니다.")
async def delete_session(session_id: str, user: User = Depends(get_current_user)):
    """Delete a session for the authenticated user.

    Args:
        session_id: The ID of the session to delete
        user: The authenticated user

    Returns:
        None
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)

        # Verify session exists and belongs to user
        session = await db_service.get_session(sanitized_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot delete other sessions")

        # Delete the session
        await db_service.delete_session(sanitized_session_id)

        logger.info("session_deleted", session_id=session_id, user_id=user.id)
    except ValueError as ve:
        logger.error("session_deletion_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.get(
    "/sessions",
    response_model=List[SessionResponse],
    summary="사용자 세션 목록 조회",
    description="인증된 사용자의 모든 세션을 조회합니다.",
)
async def get_user_sessions(user: User = Depends(get_current_user)):
    """Get all session IDs for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        List[SessionResponse]: List of session IDs
    """
    try:
        sessions = await db_service.get_user_sessions(user.id)
        return [
            SessionResponse(
                session_id=sanitize_string(session.id),
                name=sanitize_string(session.name),
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.error("get_sessions_validation_failed", user_id=user.id, error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
