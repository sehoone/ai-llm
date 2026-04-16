"""Pydantic schemas for Workflow CRUD."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field(default="")
    definition: dict = Field(default_factory=lambda: {"nodes": [], "edges": []})


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    definition: Optional[dict] = None
    is_published: Optional[bool] = None


class WorkflowResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: str
    definition: dict
    is_published: bool
    webhook_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowListItem(BaseModel):
    """Lightweight response used in list endpoints — omits definition payload."""

    id: str
    user_id: int
    name: str
    description: str
    is_published: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
