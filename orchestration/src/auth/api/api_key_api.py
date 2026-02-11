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
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID not found")
    return api_key_service.create_api_key(session, current_user.id, key_data)

@router.get("/", response_model=List[ApiKeyRead])
def get_api_keys(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(database_service.get_db_session)
):
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID not found")
    return api_key_service.get_api_keys(session, current_user.id)

@router.delete("/{key_id}", response_model=ApiKeyRead)
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(database_service.get_db_session)
):
    if not current_user.id:
        raise HTTPException(status_code=400, detail="User ID not found")
    key = api_key_service.revoke_api_key(session, key_id, current_user.id)
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    return key
