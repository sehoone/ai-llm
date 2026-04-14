"""API key management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from src.common.services.database import database_service
from src.auth.schemas.api_key_schema import ApiKeyCreate, ApiKeyRead
from src.auth.services.api_key_service import api_key_service
from src.auth.api.auth_api import get_current_user
from src.user.models.user_model import User

router = APIRouter()

@router.post("/", response_model=ApiKeyRead)
def create_api_key(
    key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(database_service.get_db_session)
):
    """Create a new API key for the authenticated user.

    Args:
        key_data: API key creation parameters (name, expiry).
        current_user: The authenticated user.
        session: Database session.

    Returns:
        ApiKeyRead: The created API key info.
    """
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID not found")
    return api_key_service.create_api_key(session, current_user.id, key_data)

@router.get("/", response_model=List[ApiKeyRead])
def get_api_keys(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(database_service.get_db_session)
):
    """List all active API keys for the authenticated user.

    Args:
        current_user: The authenticated user.
        session: Database session.

    Returns:
        List[ApiKeyRead]: List of active API keys.
    """
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID not found")
    return api_key_service.get_api_keys(session, current_user.id)

@router.delete("/{key_id}", response_model=ApiKeyRead)
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(database_service.get_db_session)
):
    """Revoke (deactivate) an API key by ID.

    Args:
        key_id: The ID of the API key to revoke.
        current_user: The authenticated user (must own the key).
        session: Database session.

    Returns:
        ApiKeyRead: The revoked API key info.

    Raises:
        HTTPException: 404 if the key is not found or does not belong to the user.
    """
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID not found")
    key = api_key_service.revoke_api_key(session, key_id, current_user.id)
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    return key
