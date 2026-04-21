"""User management endpoints. Admin access required for all operations."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from src.user.schemas.user_schema import UserRead, UserCreate, UserUpdate
from src.common.services.database import database_service
from src.common.logging import logger
from src.user.models.user_model import User, UserRole
from src.auth.api.auth_api import get_current_user

router = APIRouter()


def _require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that restricts access to admin and superadmin users.

    Raises:
        HTTPException: 403 if the user does not have admin privileges.
    """
    if user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("", response_model=List[UserRead])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    current_user: User = Depends(_require_admin),
):
    """Retrieve all users. Admin only."""
    logger.info("get_users_requested", admin_id=current_user.id, skip=skip, limit=limit)
    users = await database_service.get_all_users(skip=skip, limit=limit)
    logger.info("get_users_success", count=len(users))
    return users


@router.post("", response_model=UserRead)
async def create_user_endpoint(
    user_in: UserCreate,
    current_user: User = Depends(_require_admin),
):
    """Create a new user. Admin only."""
    logger.info("create_user_requested", admin_id=current_user.id, email=user_in.email)
    if await database_service.get_user_by_email(user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = User.hash_password(user_in.password)
    user = await database_service.create_user(
        email=user_in.email,
        password=hashed_password,
        username=user_in.username,
        role=user_in.role.value if user_in.role else "user",
        status=user_in.status,
    )
    logger.info("create_user_success", admin_id=current_user.id, new_user_id=user.id)
    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(_require_admin),
):
    """Update a user. Admin only."""
    logger.info("update_user_requested", admin_id=current_user.id, target_user_id=user_id)
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = User.hash_password(update_data.pop("password"))
    if "role" in update_data and update_data["role"]:
        update_data["role"] = update_data["role"].value

    user = await database_service.update_user(user_id, update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info("update_user_success", admin_id=current_user.id, target_user_id=user_id)
    return user


@router.delete("/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    current_user: User = Depends(_require_admin),
):
    """Delete a user. Admin only."""
    logger.info("delete_user_requested", admin_id=current_user.id, target_user_id=user_id)
    success = await database_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info("delete_user_success", admin_id=current_user.id, target_user_id=user_id)
    return {"status": "success"}


@router.get("/{user_id}", response_model=UserRead)
async def get_user_endpoint(
    user_id: int,
    current_user: User = Depends(_require_admin),
):
    """Get user by ID. Admin only."""
    logger.info("get_user_requested", admin_id=current_user.id, target_user_id=user_id)
    user = await database_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
