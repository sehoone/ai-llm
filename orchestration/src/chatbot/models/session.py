"""This file contains the session model for the application."""

from sqlmodel import Field

from src.common.models.base import BaseModel


class Session(BaseModel, table=True):
    """Session model for storing chat sessions.

    Attributes:
        id: The primary key
        user_id: The user ID who owns this session
        name: Name of the session (defaults to empty string)
        created_at: When the session was created
    """

    id: str = Field(primary_key=True)
    user_id: int = Field(index=True)
    name: str = Field(default="")
