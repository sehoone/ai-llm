"""workflow 도메인 라우터 (ADR-0019 §4).

- `router` (인증): CRUD·node-types·실행·이력·스케줄·엔드포인트·웹훅. 경로/바디는 web `src/api/workflows.ts` 고정.
  비스트림 응답은 `ApiResponse[T]`로 감싸고(axios 자동 unwrap), 실행 스트림은 raw SSE.
- `trigger_router` (미인증 공개): 웹훅 `POST /webhooks/{token}`, 동적 `ANY /run/{path}`. 미발행 워크플로우는
  Bearer 토큰(선택 인증)을 요구한다(artifact public_router 전례와 동일 패턴).
"""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.core.security import decode_access_token
from src.platform.auth.dependencies import get_current_user
from src.platform.user.model import User
from src.platform.user.repository import UserRepository
from src.domains.workflow.schema import (
    EndpointCreateRequest,
    EndpointUpdateRequest,
    ExecutionListItem,
    NodeTypeResponse,
    RunRequest,
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
    WebhookResponse,
    WorkflowCreateRequest,
    WorkflowEndpointResponse,
    WorkflowExecutionResponse,
    WorkflowListItem,
    WorkflowResponse,
    WorkflowScheduleResponse,
    WorkflowUpdateRequest,
)
from src.domains.workflow.service import WorkflowService, coerce_input

router = APIRouter()
trigger_router = APIRouter()

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _exec_response(svc: WorkflowService, execution) -> WorkflowExecutionResponse:
    return WorkflowExecutionResponse.from_model(execution, svc.node_executions(execution.id))


# ── 노드 팔레트 (⚠️ /{id}보다 먼저 선언 — 경로 충돌 방지) ──
@router.get("/node-types", response_model=ApiResponse[list[NodeTypeResponse]])
def get_node_types(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[NodeTypeResponse]]:
    rows = WorkflowService(session).node_types()
    return ApiResponse.ok([NodeTypeResponse(**r) for r in rows])


# ── 실행 이력 (단건 — /{id}보다 먼저) ──
@router.get("/executions/{execution_id}", response_model=ApiResponse[WorkflowExecutionResponse])
def get_execution(
    execution_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowExecutionResponse]:
    svc = WorkflowService(session)
    e = svc.get_execution(execution_id, user)
    return ApiResponse.ok(_exec_response(svc, e))


# ── Workflow CRUD ──
@router.get("", response_model=ApiResponse[list[WorkflowListItem]])
def list_workflows(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[WorkflowListItem]]:
    rows = WorkflowService(session).list(user, limit, offset)
    return ApiResponse.ok([WorkflowListItem.from_model(w) for w in rows])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[WorkflowResponse])
def create_workflow(
    req: WorkflowCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowResponse]:
    w = WorkflowService(session).create(user, req)
    return ApiResponse.ok(WorkflowResponse.from_model(w))


@router.get("/{workflow_id}", response_model=ApiResponse[WorkflowResponse])
def get_workflow(
    workflow_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowResponse]:
    w = WorkflowService(session).get(workflow_id, user)
    return ApiResponse.ok(WorkflowResponse.from_model(w))


@router.put("/{workflow_id}", response_model=ApiResponse[WorkflowResponse])
def update_workflow(
    workflow_id: str,
    req: WorkflowUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowResponse]:
    w = WorkflowService(session).update(workflow_id, user, req)
    return ApiResponse.ok(WorkflowResponse.from_model(w))


@router.delete("/{workflow_id}", response_model=ApiResponse[None])
def delete_workflow(
    workflow_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    WorkflowService(session).delete(workflow_id, user)
    return ApiResponse.ok(None)


@router.patch("/{workflow_id}/publish", response_model=ApiResponse[WorkflowResponse])
def toggle_publish(
    workflow_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowResponse]:
    w = WorkflowService(session).toggle_publish(workflow_id, user)
    return ApiResponse.ok(WorkflowResponse.from_model(w))


# ── 실행 ──
@router.post(
    "/{workflow_id}/executions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[WorkflowExecutionResponse],
)
async def run_workflow(
    workflow_id: str,
    req: RunRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowExecutionResponse]:
    svc = WorkflowService(session)
    w = svc.get(workflow_id, user)
    execution = await svc.execute(w, req.input_data, user.id)
    return ApiResponse.ok(_exec_response(svc, execution))


@router.post("/{workflow_id}/executions/stream")
async def run_workflow_stream(
    workflow_id: str,
    req: RunRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    svc = WorkflowService(session)
    w = svc.get(workflow_id, user)
    stream = svc.execute_stream(w, req.input_data, user.id)
    return StreamingResponse(stream, media_type="text/event-stream", headers=_SSE_HEADERS)


@router.get("/{workflow_id}/executions", response_model=ApiResponse[list[ExecutionListItem]])
def list_executions(
    workflow_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[ExecutionListItem]]:
    rows = WorkflowService(session).list_executions(workflow_id, user)
    return ApiResponse.ok([ExecutionListItem.from_model(e) for e in rows])


# ── 웹훅 ──
@router.patch("/{workflow_id}/webhook", response_model=ApiResponse[WebhookResponse])
def manage_webhook(
    workflow_id: str,
    action: str = Query(..., pattern="^(generate|revoke)$"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WebhookResponse]:
    token = WorkflowService(session).manage_webhook(workflow_id, user, action)
    return ApiResponse.ok(WebhookResponse(webhook_token=token))


# ── 스케줄 ──
@router.get("/{workflow_id}/schedules", response_model=ApiResponse[list[WorkflowScheduleResponse]])
def list_schedules(
    workflow_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[WorkflowScheduleResponse]]:
    rows = WorkflowService(session).list_schedules(workflow_id, user)
    return ApiResponse.ok([WorkflowScheduleResponse.from_model(s) for s in rows])


@router.post(
    "/{workflow_id}/schedules",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[WorkflowScheduleResponse],
)
def create_schedule(
    workflow_id: str,
    req: ScheduleCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowScheduleResponse]:
    s = WorkflowService(session).create_schedule(workflow_id, user, req)
    return ApiResponse.ok(WorkflowScheduleResponse.from_model(s))


@router.patch(
    "/{workflow_id}/schedules/{schedule_id}",
    response_model=ApiResponse[WorkflowScheduleResponse],
)
def update_schedule(
    workflow_id: str,
    schedule_id: str,
    req: ScheduleUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowScheduleResponse]:
    s = WorkflowService(session).update_schedule(workflow_id, schedule_id, user, req)
    return ApiResponse.ok(WorkflowScheduleResponse.from_model(s))


@router.delete("/{workflow_id}/schedules/{schedule_id}", response_model=ApiResponse[None])
def delete_schedule(
    workflow_id: str,
    schedule_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    WorkflowService(session).delete_schedule(workflow_id, schedule_id, user)
    return ApiResponse.ok(None)


# ── 동적 엔드포인트 ──
@router.get("/{workflow_id}/endpoints", response_model=ApiResponse[list[WorkflowEndpointResponse]])
def list_endpoints(
    workflow_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[list[WorkflowEndpointResponse]]:
    rows = WorkflowService(session).list_endpoints(workflow_id, user)
    return ApiResponse.ok([WorkflowEndpointResponse.from_model(e) for e in rows])


@router.post(
    "/{workflow_id}/endpoints",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[WorkflowEndpointResponse],
)
def create_endpoint(
    workflow_id: str,
    req: EndpointCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowEndpointResponse]:
    e = WorkflowService(session).create_endpoint(workflow_id, user, req)
    return ApiResponse.ok(WorkflowEndpointResponse.from_model(e))


@router.put(
    "/{workflow_id}/endpoints/{endpoint_id}",
    response_model=ApiResponse[WorkflowEndpointResponse],
)
def update_endpoint(
    workflow_id: str,
    endpoint_id: str,
    req: EndpointUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowEndpointResponse]:
    e = WorkflowService(session).update_endpoint(workflow_id, endpoint_id, user, req)
    return ApiResponse.ok(WorkflowEndpointResponse.from_model(e))


@router.delete("/{workflow_id}/endpoints/{endpoint_id}", response_model=ApiResponse[None])
def delete_endpoint(
    workflow_id: str,
    endpoint_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[None]:
    WorkflowService(session).delete_endpoint(workflow_id, endpoint_id, user)
    return ApiResponse.ok(None)


# ── 공개 트리거 (미인증 — token/발행 여부로 인가) ──
def _optional_user(request: Request, session: Session) -> User | None:
    """Authorization: Bearer <jwt>가 있으면 해석, 없거나 무효면 None(예외 없음)."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        claims = decode_access_token(token)
        return UserRepository(session).get(int(claims["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


@trigger_router.post("/webhooks/{token}", response_model=ApiResponse[WorkflowExecutionResponse])
async def trigger_webhook(
    token: str,
    request: Request,
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowExecutionResponse]:
    body = await request.body()
    svc = WorkflowService(session)
    execution = await svc.trigger_by_webhook(token, coerce_input(body))
    return ApiResponse.ok(_exec_response(svc, execution))


@trigger_router.api_route(
    "/run/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    response_model=ApiResponse[WorkflowExecutionResponse],
)
async def trigger_endpoint(
    path: str,
    request: Request,
    session: Session = Depends(get_session),
) -> ApiResponse[WorkflowExecutionResponse]:
    body = await request.body()
    caller = _optional_user(request, session)
    svc = WorkflowService(session)
    execution = await svc.trigger_by_endpoint(path, request.method, coerce_input(body), caller)
    return ApiResponse.ok(_exec_response(svc, execution))
