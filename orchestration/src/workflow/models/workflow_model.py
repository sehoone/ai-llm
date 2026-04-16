"""Workflow and related DB models."""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel


class Workflow(SQLModel, table=True):
    """Workflow definition model.

    Stores the node/edge graph definition as a JSON blob alongside metadata.
    The `definition` field follows React Flow's node/edge schema so the frontend
    can round-trip the canvas state without transformation.
    """

    __tablename__ = "workflow"

    id: str = Field(primary_key=True)
    user_id: int = Field(index=True)
    name: str = Field(max_length=200)
    description: str = Field(default="", sa_column=Column(Text))
    # {nodes: [...], edges: [...]}  — React Flow compatible
    definition: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    is_published: bool = Field(default=False)
    # Webhook: set to a UUID secret to enable; None = disabled
    webhook_token: Optional[str] = Field(default=None, nullable=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
