"""This file contains the user model for the application."""

from enum import Enum
from typing import Optional
import bcrypt
from sqlalchemy import String
from sqlmodel import Field

from src.common.models.base import BaseModel

class UserRole(str, Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    CASHIER = "CASHIER"
    USER = "USER"

class User(BaseModel, table=True):
    """User model for storing user accounts."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str = Field(default="")
    role: UserRole = Field(default=UserRole.USER, sa_type=String)
    status: str = Field(default="active")

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash."""
        if not self.hashed_password:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), self.hashed_password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
