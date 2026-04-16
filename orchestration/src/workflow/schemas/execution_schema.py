"""Pydantic schemas for Workflow execution."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from src.workflow.models.execution_model import ExecutionStatus


class ExecutionCreate(BaseModel):
    """Input payload when triggering a workflow run."""

    input_data: dict = {}


class NodeExecutionResponse(BaseModel):
    id: str
    execution_id: str
    node_id: str
    node_type: str
    status: ExecutionStatus
    input_data: dict
    output_data: Optional[dict]
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    user_id: int
    status: ExecutionStatus
    input_data: dict
    output_data: Optional[dict]
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    node_executions: list[NodeExecutionResponse] = []

    model_config = {"from_attributes": True}


class ExecutionListItem(BaseModel):
    id: str
    workflow_id: str
    status: ExecutionStatus
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── SSE event shapes ──────────────────────────────────────────────────────────

class SSEEvent(BaseModel):
    """Base SSE event."""

    type: str


class NodeStartEvent(SSEEvent):
    type: str = "node_start"
    node_id: str
    node_type: str
    input_data: dict


class NodeCompleteEvent(SSEEvent):
    type: str = "node_complete"
    node_id: str
    node_type: str
    output_data: dict


class NodeFailedEvent(SSEEvent):
    type: str = "node_failed"
    node_id: str
    node_type: str
    error: str


class NodeSkippedEvent(SSEEvent):
    type: str = "node_skipped"
    node_id: str


class ExecutionCompleteEvent(SSEEvent):
    type: str = "execution_complete"
    execution_id: str
    output_data: dict


class ExecutionFailedEvent(SSEEvent):
    type: str = "execution_failed"
    execution_id: str
    error: str
