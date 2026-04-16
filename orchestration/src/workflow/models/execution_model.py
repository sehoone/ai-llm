"""Workflow execution DB models."""

import enum
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowExecution(SQLModel, table=True):
    """Records a single run of a Workflow.

    Created the moment a workflow is triggered.  Status transitions:
    pending → running → completed | failed
    """

    __tablename__ = "workflow_execution"

    id: str = Field(primary_key=True)
    workflow_id: str = Field(index=True)
    user_id: int = Field(index=True)
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)
    input_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    output_data: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    error: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = Field(default=None, nullable=True)


class NodeExecution(SQLModel, table=True):
    """Records the execution of a single node within a WorkflowExecution."""

    __tablename__ = "workflow_node_execution"

    id: str = Field(primary_key=True)
    execution_id: str = Field(index=True)
    node_id: str  # frontend canvas node id
    node_type: str
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)
    input_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    output_data: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    error: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = Field(default=None, nullable=True)
