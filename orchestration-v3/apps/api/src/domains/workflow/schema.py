"""workflow 도메인 DTO. web `src/api/workflows.ts` 타입과 1:1 (ADR-0019 §4).

비스트림 응답은 라우터에서 `ApiResponse[T]`로 감싼다(web axios 인터셉터가 자동 unwrap).
`definition`은 React Flow 캔버스 상태를 무변환 round-trip하기 위해 느슨한 dict 컨테이너로 둔다.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.domains.workflow.model import (
    NodeExecution,
    Workflow,
    WorkflowEndpoint,
    WorkflowExecution,
    WorkflowSchedule,
)


# ── 정의(그래프) ──
class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")
    nodes: list[dict] = []
    edges: list[dict] = []


# ── Workflow CRUD ──
class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    definition: WorkflowDefinition = Field(default_factory=WorkflowDefinition)


class WorkflowUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    definition: WorkflowDefinition | None = None
    is_published: bool | None = None


class WorkflowResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: str
    definition: dict
    is_published: bool
    webhook_token: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, w: Workflow) -> "WorkflowResponse":
        return cls(
            id=w.id, user_id=w.user_id, name=w.name, description=w.description,
            definition=w.definition or {}, is_published=w.is_published,
            webhook_token=w.webhook_token, created_at=w.created_at, updated_at=w.updated_at,
        )


class WorkflowListItem(BaseModel):
    id: str
    user_id: int
    name: str
    description: str
    is_published: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, w: Workflow) -> "WorkflowListItem":
        return cls(
            id=w.id, user_id=w.user_id, name=w.name, description=w.description,
            is_published=w.is_published, created_at=w.created_at, updated_at=w.updated_at,
        )


# ── 실행 ──
class RunRequest(BaseModel):
    input_data: dict = {}


class NodeExecutionResponse(BaseModel):
    id: str
    execution_id: str
    node_id: str
    node_type: str
    status: str
    input_data: dict
    output_data: dict | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_model(cls, n: NodeExecution) -> "NodeExecutionResponse":
        return cls(
            id=n.id, execution_id=n.execution_id, node_id=n.node_id, node_type=n.node_type,
            status=str(n.status), input_data=n.input_data or {}, output_data=n.output_data,
            error=n.error, created_at=n.created_at, completed_at=n.completed_at,
        )


class WorkflowExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    user_id: int
    status: str
    input_data: dict
    output_data: dict | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None
    node_executions: list[NodeExecutionResponse] = []

    @classmethod
    def from_model(
        cls, e: WorkflowExecution, node_execs: list[NodeExecution]
    ) -> "WorkflowExecutionResponse":
        return cls(
            id=e.id, workflow_id=e.workflow_id, user_id=e.user_id, status=str(e.status),
            input_data=e.input_data or {}, output_data=e.output_data, error=e.error,
            created_at=e.created_at, completed_at=e.completed_at,
            node_executions=[NodeExecutionResponse.from_model(n) for n in node_execs],
        )


class ExecutionListItem(BaseModel):
    id: str
    workflow_id: str
    status: str
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_model(cls, e: WorkflowExecution) -> "ExecutionListItem":
        return cls(
            id=e.id, workflow_id=e.workflow_id, status=str(e.status),
            created_at=e.created_at, completed_at=e.completed_at,
        )


# ── 노드 팔레트 ──
class NodeTypeResponse(BaseModel):
    type: str
    input_schema: dict
    output_schema: dict


# ── 스케줄 ──
class ScheduleCreateRequest(BaseModel):
    label: str = ""
    cron_expr: str = Field(min_length=1, max_length=100)
    input_data: dict = {}


class ScheduleUpdateRequest(BaseModel):
    label: str | None = None
    cron_expr: str | None = Field(default=None, max_length=100)
    input_data: dict | None = None
    is_active: bool | None = None


class WorkflowScheduleResponse(BaseModel):
    id: str
    workflow_id: str
    label: str
    cron_expr: str
    input_data: dict
    is_active: bool
    created_at: datetime
    next_run_at: datetime | None

    @classmethod
    def from_model(cls, s: WorkflowSchedule) -> "WorkflowScheduleResponse":
        return cls(
            id=s.id, workflow_id=s.workflow_id, label=s.label, cron_expr=s.cron_expr,
            input_data=s.input_data or {}, is_active=s.is_active,
            created_at=s.created_at, next_run_at=s.next_run_at,
        )


# ── 동적 엔드포인트 ──
class EndpointCreateRequest(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    method: str = "POST"
    description: str = ""
    is_active: bool = True


class EndpointUpdateRequest(BaseModel):
    path: str | None = Field(default=None, max_length=500)
    method: str | None = None
    description: str | None = None
    is_active: bool | None = None


class WorkflowEndpointResponse(BaseModel):
    id: str
    workflow_id: str
    user_id: int
    path: str
    method: str
    is_active: bool
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, e: WorkflowEndpoint) -> "WorkflowEndpointResponse":
        return cls(
            id=e.id, workflow_id=e.workflow_id, user_id=e.user_id, path=e.path, method=e.method,
            is_active=e.is_active, description=e.description,
            created_at=e.created_at, updated_at=e.updated_at,
        )


# ── 웹훅 ──
class WebhookResponse(BaseModel):
    webhook_token: str | None
