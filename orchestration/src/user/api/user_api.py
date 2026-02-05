from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from src.user.schemas.user_schema import UserRead, UserCreate, UserUpdate
from src.common.services.database import DatabaseService
from src.user.models.user_model import User
from src.auth.api.auth_api import get_current_user

router = APIRouter()
db_service = DatabaseService()

@router.get("/", response_model=List[UserRead])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all users.
    Only admins should be able to access this.
    """
    # TODO: Add role check
    return await db_service.get_all_users(skip=skip, limit=limit)

@router.post("/", response_model=UserRead)
async def create_user_endpoint(
    user_in: UserCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new user.
    Only admins should be able to create users.
    """
    # TODO: Add role check
    if await db_service.get_user_by_email(user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password if provided
    hashed_password = User.hash_password(user_in.password)
    
    user = await db_service.create_user(
        email=user_in.email,
        password=hashed_password,
        username=user_in.username,
        role=user_in.role.value if user_in.role else "user",
        status=user_in.status
    )
    return user

@router.put("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update a user.
    """
    # Handle password hashing if included in update
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = User.hash_password(update_data.pop("password"))
    
    if "role" in update_data and update_data["role"]:
         update_data["role"] = update_data["role"].value

    user = await db_service.update_user(user_id, update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a user.
    """
    success = await db_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}

@router.get("/{user_id}", response_model=UserRead)
async def get_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get user by ID.
    """
    user = await db_service.get_user(user_id)
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
    return user
