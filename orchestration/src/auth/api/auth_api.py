"""Authentication and authorization endpoints for the API.

This module provides endpoints for user registration, login, session management,
and token verification.
"""

from datetime import timedelta

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
from sqlmodel import Session

from src.auth.services.api_key_service import api_key_service
from src.common.config import settings
from src.common.limiter import limiter
from src.common.logging import (
    bind_context,
    logger,
)
from src.user.models.user_model import User
from src.auth.schemas.auth_schema import (
    RefreshTokenRequest,
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
    session: Session = Depends(db_service.get_db_session),
) -> User:
    """Get the current user ID from the token or API key.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token or API key.
        session: Database session.

    Returns:
        User: The user extracted from the token.

    Raises:
        HTTPException: If the token is invalid or missing.
    """
    try:
        # Sanitize token
        token = sanitize_string(credentials.credentials)

        # Check for API Key (Database backed)
        # We need to check the DB if it is a "tracked" key or if it starts with sk- (legacy/UUID)
        # But now we use JWT for everything.
        # How to know if we should check the DB revocation list?
        # 1. If it has a specific claim "type": "api_key"
        # 2. Or we just decode it.
        
        payload = verify_token(token)
        if payload is None:
             # It might be a raw opaque token (sk-...)
            if token.startswith("sk-"):
                 # Legacy opaque token support
                api_key = api_key_service.get_api_key_by_token(session, token)
                if not api_key:
                    raise HTTPException(status_code=401, detail="Invalid API Key")
                user = await db_service.get_user(api_key.user_id)
                if user:
                    bind_context(user_id=user.id)
                    return user
            
            # Invalid JWT and not an opaque token
            logger.error("invalid_token_payload", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        # If it is an API Key JWT, we MUST check if it is still active in the DB
        if token_type == "api_key":
            # The "key" stored in DB matches the JWT string
            api_key = api_key_service.get_api_key_by_token(session, token)
            if not api_key:
                 # Revoked or deleted
                 logger.warning("api_key_revoked_or_not_found", user_id=user_id)
                 raise HTTPException(status_code=401, detail="API Key is invalid or revoked")
                 
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
        username = user_data.username
        if not username:
             username = sanitized_email.split("@")[0]

        user = await db_service.create_user(
            email=sanitized_email,
            password=User.hash_password(password),
            username=username,
        )

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



