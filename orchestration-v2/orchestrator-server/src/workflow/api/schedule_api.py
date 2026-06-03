"""Schedule CRUD endpoints.

POST   /workflows/{id}/schedules          — create cron schedule
GET    /workflows/{id}/schedules          — list schedules for workflow
PATCH  /workflows/{id}/schedules/{sid}    — update schedule (cron/label/active)
DELETE /workflows/{id}/schedules/{sid}    — delete schedule
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from typing import Optional

from src.auth.api.auth_api import get_current_user
from src.common.logging import logger
from src.common.services.database import database_service
from src.user.models.user_model import User
from src.workflow.services.scheduler import workflow_scheduler

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


# ── Schemas ───────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    label: str = ""
    cron_expr: str           # "0 9 * * 1-5"
    input_data: dict = {}


class ScheduleUpdate(BaseModel):
    label: Optional[str] = None
    cron_expr: Optional[str] = None
    input_data: Optional[dict] = None
    is_active: Optional[bool] = None


class ScheduleResponse(BaseModel):
    id: str
    workflow_id: str
    label: str
    cron_expr: str
    input_data: dict
    is_active: bool
    created_at: str
    next_run_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/{workflow_id}/schedules",
    response_model=ScheduleResponse,
    status_code=201,
    summary="스케줄 생성",
)
async def create_schedule(
    workflow_id: str,
    body: ScheduleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _owned_workflow(workflow_id, user, db)
    schedule = database_service.create_schedule(
        db,
        workflow_id=workflow_id,
        user_id=user.id,
        label=body.label,
        cron_expr=body.cron_expr,
        input_data=body.input_data,
    )
    workflow_scheduler.add_schedule(schedule)
    logger.info("schedule_created", schedule_id=schedule.id, workflow_id=workflow_id)
    return _to_response(schedule)


@router.get(
    "/{workflow_id}/schedules",
    response_model=list[ScheduleResponse],
    summary="스케줄 목록",
)
async def list_schedules(
    workflow_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _owned_workflow(workflow_id, user, db)
    schedules = database_service.list_schedules(db, workflow_id)
    return [_to_response(s) for s in schedules]


@router.patch(
    "/{workflow_id}/schedules/{schedule_id}",
    response_model=ScheduleResponse,
    summary="스케줄 수정",
)
async def update_schedule(
    workflow_id: str,
    schedule_id: str,
    body: ScheduleUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _owned_workflow(workflow_id, user, db)
    schedule = database_service.get_schedule(db, schedule_id)
    if not schedule or schedule.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_fields = body.model_dump(exclude_none=True)
    schedule = database_service.update_schedule(db, schedule, **update_fields)

    # Sync scheduler
    workflow_scheduler.add_schedule(schedule)
    if not schedule.is_active:
        workflow_scheduler.pause_schedule(schedule.id)
    else:
        workflow_scheduler.resume_schedule(schedule.id)

    return _to_response(schedule)


@router.delete(
    "/{workflow_id}/schedules/{schedule_id}",
    status_code=204,
    summary="스케줄 삭제",
)
async def delete_schedule(
    workflow_id: str,
    schedule_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _owned_workflow(workflow_id, user, db)
    schedule = database_service.get_schedule(db, schedule_id)
    if not schedule or schedule.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    workflow_scheduler.remove_schedule(schedule.id)
    database_service.delete_schedule(db, schedule)
    logger.info("schedule_deleted", schedule_id=schedule_id)


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_response(s) -> ScheduleResponse:
    return ScheduleResponse(
        id=s.id,
        workflow_id=s.workflow_id,
        label=s.label or "",
        cron_expr=s.cron_expr,
        input_data=s.input_data or {},
        is_active=s.is_active,
        created_at=s.created_at.isoformat(),
        next_run_at=s.next_run_at.isoformat() if s.next_run_at else None,
    )
