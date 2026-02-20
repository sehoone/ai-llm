"""This file contains the GPT session model for the application."""

from typing import Optional

from sqlmodel import Field

from src.common.models.base import BaseModel


class GPTSession(BaseModel, table=True):
    """Session model for storing Custom GPT chat sessions.

    Attributes:
        id: The primary key
        user_id: The user ID who owns this session
        custom_gpt_id: The Custom GPT ID this session belongs to
        name: Name of the session (defaults to empty string)
        created_at: When the session was created
    """
    __tablename__ = "gpt_session"

    id: str = Field(primary_key=True)
    user_id: int = Field(index=True)
    custom_gpt_id: str = Field(index=True, foreign_key="custom_gpt.id")
    name: str = Field(default="")
