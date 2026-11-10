"""workflow 도메인 테이블. schema: llmonl. V2 workflow*·node_execution 포팅 (ADR-0019 §3).

- `workflow`: React Flow `{nodes,edges}` 정의 + 메타 + webhook_token.
- `workflow_execution`: 실행 1회 레코드.
- `workflow_node_execution`: 실행 내 노드별 레코드.
- `workflow_schedule`: cron 스케줄(APScheduler job_id = PK).
- `workflow_endpoint`: 동적 API 경로 바인딩((path,method) unique).

FK 없음 — 연쇄 정리는 repository가 명시 수행(다른 도메인 관례와 동일).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import NaiveDatetime
from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Workflow(SQLModel, table=True):
    __tablename__ = "workflow"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: int = Field(index=True)
    name: str = Field(max_length=200)
    description: str = Field(default="", sa_column=Column(Text))
    # {nodes: [...], edges: [...]} — React Flow 호환
    definition: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    is_published: bool = Field(default=False)
    webhook_token: str | None = Field(default=None, nullable=True, index=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class WorkflowExecution(SQLModel, table=True):
    __tablename__ = "workflow_execution"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    workflow_id: str = Field(index=True)
    user_id: int = Field(index=True)
    # VARCHAR(20) — ExecutionStatus 값(str-enum)을 저장. 다른 도메인(meeting)과 동일한 str 컬럼 관례.
    status: str = Field(default=ExecutionStatus.PENDING.value, max_length=20)
    input_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    output_data: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    completed_at: NaiveDatetime | None = Field(default=None, nullable=True)


class NodeExecution(SQLModel, table=True):
    __tablename__ = "workflow_node_execution"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    execution_id: str = Field(index=True)
    node_id: str
    node_type: str
    # VARCHAR(20) — ExecutionStatus 값(str-enum)을 저장. 다른 도메인(meeting)과 동일한 str 컬럼 관례.
    status: str = Field(default=ExecutionStatus.PENDING.value, max_length=20)
    input_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    output_data: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    completed_at: NaiveDatetime | None = Field(default=None, nullable=True)


class WorkflowSchedule(SQLModel, table=True):
    __tablename__ = "workflow_schedule"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)  # APScheduler job_id
    workflow_id: str = Field(index=True)
    user_id: int = Field(index=True)
    label: str = Field(default="", max_length=200)
    cron_expr: str = Field(max_length=100)
    input_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    is_active: bool = Field(default=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    next_run_at: NaiveDatetime | None = Field(default=None, nullable=True)


class WorkflowEndpoint(SQLModel, table=True):
    __tablename__ = "workflow_endpoint"
    __table_args__ = (
        UniqueConstraint("path", "method", name="uq_endpoint_path_method"),
        {"schema": "llmonl"},
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    workflow_id: str = Field(index=True)
    user_id: int = Field(index=True)
    path: str = Field(max_length=500, index=True)  # /api/v1/run/ 뒤 접미사
    method: str = Field(default="POST", max_length=10)
    is_active: bool = Field(default=True)
    description: str = Field(default="", sa_column=Column(Text))
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
