"""WorkflowEndpoint DB model — maps a custom HTTP path to a workflow."""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class WorkflowEndpoint(SQLModel, table=True):
    """Dynamic API endpoint bound to a workflow.

    `path` is the user-defined suffix after the fixed prefix `/api/v1/run/`.
    `method` is the HTTP method this endpoint responds to.
    The combination of (path, method) must be globally unique.
    """

    __tablename__ = "workflow_endpoint"
    __table_args__ = (UniqueConstraint("path", "method", name="uq_endpoint_path_method"),)

    id: str = Field(primary_key=True)
    workflow_id: str = Field(index=True)
    user_id: int = Field(index=True)
    # e.g. "summarize", "v2/translate", "my-bot/chat"
    path: str = Field(max_length=500, index=True)
    method: str = Field(default="POST", max_length=10)  # GET POST PUT PATCH DELETE
    is_active: bool = Field(default=True)
    description: str = Field(default="", sa_column=Column(Text))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
