"""Workflow CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from src.auth.api.auth_api import get_current_user
from src.common.logging import logger
from src.common.services.database import database_service
from src.user.models.user_model import User
from src.workflow.schemas.workflow_schema import (
    WorkflowCreate,
    WorkflowListItem,
    WorkflowResponse,
    WorkflowUpdate,
)
from src.workflow.services.executor.registry import list_node_types

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


# ── Node type metadata (palette) ──────────────────────────────────────────────

@router.get("/node-types", summary="사용 가능한 노드 타입 목록")
async def get_node_types():
    """Return all registered node types with their config schemas.

    The frontend uses this to render the node palette and config panel forms.
    """
    return list_node_types()


# ── Workflow CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[WorkflowListItem], summary="워크플로우 목록")
async def list_workflows(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    return database_service.list_workflows(db, user_id=user.id, limit=limit, offset=offset)


@router.post("", response_model=WorkflowResponse, status_code=201, summary="워크플로우 생성")
async def create_workflow(
    body: WorkflowCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    workflow = database_service.create_workflow(
        db,
        user_id=user.id,
        name=body.name,
        description=body.description,
        definition=body.definition,
    )
    logger.info("workflow_created", workflow_id=workflow.id, user_id=user.id)
    return workflow


@router.get("/{workflow_id}", response_model=WorkflowResponse, summary="워크플로우 상세")
async def get_workflow(
    workflow_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    return _owned_workflow(workflow_id, user, db)


@router.put("/{workflow_id}", response_model=WorkflowResponse, summary="워크플로우 수정")
async def update_workflow(
    workflow_id: str,
    body: WorkflowUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    workflow = _owned_workflow(workflow_id, user, db)
    updated = database_service.update_workflow(
        db,
        workflow,
        name=body.name,
        description=body.description,
        definition=body.definition,
        is_published=body.is_published,
    )
    logger.info("workflow_updated", workflow_id=workflow_id, user_id=user.id)
    return updated


@router.delete("/{workflow_id}", status_code=204, summary="워크플로우 삭제")
async def delete_workflow(
    workflow_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    workflow = _owned_workflow(workflow_id, user, db)
    database_service.delete_workflow(db, workflow)
    logger.info("workflow_deleted", workflow_id=workflow_id, user_id=user.id)


@router.patch("/{workflow_id}/publish", response_model=WorkflowResponse, summary="워크플로우 발행/해제")
async def toggle_publish(
    workflow_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    workflow = _owned_workflow(workflow_id, user, db)
    updated = database_service.update_workflow(db, workflow, is_published=not workflow.is_published)
    logger.info("workflow_publish_toggled", workflow_id=workflow_id, is_published=updated.is_published)
    return updated
