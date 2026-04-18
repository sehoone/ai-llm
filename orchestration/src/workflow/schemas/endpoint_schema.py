"""Pydantic schemas for WorkflowEndpoint CRUD."""

import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

_VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_PATH_RE = re.compile(r"^[a-zA-Z0-9_\-][a-zA-Z0-9_\-/]*$")


class EndpointCreate(BaseModel):
    path: str = Field(..., max_length=500, description="URL suffix after /api/v1/run/")
    method: str = Field(default="POST")
    description: str = Field(default="")
    is_active: bool = Field(default=True)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        v = v.strip("/").lower()
        if not v:
            raise ValueError("path must not be empty")
        if not _PATH_RE.match(v):
            raise ValueError("path may only contain letters, numbers, hyphens, underscores, and /")
        return v

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        v = v.upper()
        if v not in _VALID_METHODS:
            raise ValueError(f"method must be one of {sorted(_VALID_METHODS)}")
        return v


class EndpointUpdate(BaseModel):
    path: Optional[str] = Field(default=None, max_length=500)
    method: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip("/").lower()
        if not v:
            raise ValueError("path must not be empty")
        if not _PATH_RE.match(v):
            raise ValueError("path may only contain letters, numbers, hyphens, underscores, and /")
        return v

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.upper()
        if v not in _VALID_METHODS:
            raise ValueError(f"method must be one of {sorted(_VALID_METHODS)}")
        return v


class EndpointResponse(BaseModel):
    id: str
    workflow_id: str
    user_id: int
    path: str
    method: str
    is_active: bool
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
