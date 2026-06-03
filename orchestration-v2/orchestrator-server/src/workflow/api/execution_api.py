"""Workflow execution endpoints.

POST  /workflows/{id}/executions         → trigger + return final result (sync)
POST  /workflows/{id}/executions/stream  → trigger + SSE real-time events
GET   /workflows/{id}/executions         → execution history list
GET   /executions/{exec_id}             → execution detail with node executions
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from src.auth.api.auth_api import get_current_user
from src.common.logging import logger
from src.common.services.database import database_service
from src.user.models.user_model import User
from src.workflow.schemas.execution_schema import (
    ExecutionCreate,
    ExecutionListItem,
    ExecutionResponse,
    NodeExecutionResponse,
)
from src.workflow.services.executor.engine import workflow_engine

router = APIRouter()


def _get_db():
    with Session(database_service.engine) as session:
        yield session


def _owned_workflow(workflow_id: str, user: User, db: Session):
    workflow = database_service.get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return workflow


# ── Trigger (sync) ────────────────────────────────────────────────────────────

@router.post(
    "/{workflow_id}/executions",
    response_model=ExecutionResponse,
    status_code=201,
    summary="워크플로우 실행 (동기)",
)
async def run_workflow(
    workflow_id: str,
    body: ExecutionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Trigger a workflow and wait for completion.  Returns the full execution record."""
    workflow = _owned_workflow(workflow_id, user, db)

    try:
        execution = await workflow_engine.execute(
            workflow=workflow,
            input_data=body.input_data,
            user_id=user.id,
            db=db,
        )
    except Exception as exc:
        logger.error("workflow_run_failed", workflow_id=workflow_id, error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    node_execs = database_service.list_node_executions(db, execution.id)
    return ExecutionResponse(
        **execution.model_dump(),
        node_executions=[NodeExecutionResponse.model_validate(ne) for ne in node_execs],
    )


# ── Trigger (SSE stream) ──────────────────────────────────────────────────────

@router.post(
    "/{workflow_id}/executions/stream",
    summary="워크플로우 실행 (SSE 스트림)",
    response_class=StreamingResponse,
)
async def run_workflow_stream(
    workflow_id: str,
    body: ExecutionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Trigger a workflow and stream execution events via SSE.

    Each event is a JSON object with a `type` field:
    - `node_start`         — node began executing
    - `node_complete`      — node finished successfully
    - `node_failed`        — node failed
    - `node_skipped`       — node was skipped (condition branch)
    - `execution_complete` — workflow finished
    - `execution_failed`   — workflow failed
    """
    workflow = _owned_workflow(workflow_id, user, db)

    logger.info("workflow_stream_started", workflow_id=workflow_id, user_id=user.id)

    return StreamingResponse(
        workflow_engine.execute_stream(
            workflow=workflow,
            input_data=body.input_data,
            user_id=user.id,
            db=db,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ── Execution history ─────────────────────────────────────────────────────────

@router.get(
    "/{workflow_id}/executions",
    response_model=list[ExecutionListItem],
    summary="실행 목록",
)
async def list_executions(
    workflow_id: str,
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _owned_workflow(workflow_id, user, db)
    return database_service.list_executions(db, workflow_id=workflow_id, limit=limit, offset=offset)


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    summary="실행 상세",
)
async def get_execution(
    execution_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    execution = database_service.get_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    node_execs = database_service.list_node_executions(db, execution_id)
    return ExecutionResponse(
        **execution.model_dump(),
        node_executions=[NodeExecutionResponse.model_validate(ne) for ne in node_execs],
    )
