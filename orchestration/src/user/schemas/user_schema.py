from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from src.user.models.user_model import UserRole

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole = UserRole.USER
    status: str = "active"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    status: Optional[str] = None
    password: Optional[str] = None

class UserRead(UserBase):
    id: int
    
    class Config:
        from_attributes = True
