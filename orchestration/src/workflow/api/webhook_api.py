"""Webhook trigger endpoints.

PATCH /workflows/{id}/webhook          — generate or revoke a webhook token
POST  /api/v1/webhooks/{token}         — public trigger (no auth, token-based)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from src.auth.api.auth_api import get_current_user
from src.common.logging import logger
from src.common.services.database import database_service
from src.user.models.user_model import User
from src.workflow.services.executor.engine import workflow_engine
from src.workflow.schemas.execution_schema import ExecutionCreate

router = APIRouter()
webhook_router = APIRouter()  # mounted at /webhooks


# ── Manage webhook token (authenticated) ─────────────────────────────────────

def _get_db():
    with Session(database_service.engine) as session:
        yield session


@router.patch(
    "/{workflow_id}/webhook",
    summary="Webhook 토큰 생성/삭제",
)
async def manage_webhook(
    workflow_id: str,
    action: str = "generate",  # "generate" | "revoke"
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Generate (action=generate) or revoke (action=revoke) a webhook token."""
    workflow = database_service.get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if action == "revoke":
        token = None
    else:
        token = str(uuid.uuid4()).replace("-", "")

    updated = database_service.update_workflow(db, workflow, webhook_token=token)
    return {"webhook_token": updated.webhook_token}


# ── Public webhook trigger ────────────────────────────────────────────────────

@webhook_router.post(
    "/{token}",
    summary="Webhook 워크플로우 실행",
)
async def trigger_webhook(
    token: str,
    body: ExecutionCreate | None = None,
    db: Session = Depends(_get_db),
):
    """Fire a workflow via its webhook token.  No user auth required."""
    workflow = database_service.get_workflow_by_token(db, token)
    if not workflow:
        raise HTTPException(status_code=404, detail="Invalid webhook token")

    if not workflow.is_published:
        raise HTTPException(status_code=403, detail="Workflow is not published")

    input_data = body.input_data if body else {}
    logger.info("webhook_triggered", workflow_id=workflow.id)

    try:
        execution = await workflow_engine.execute(
            workflow=workflow,
            input_data=input_data,
            user_id=workflow.user_id,
            db=db,
        )
    except Exception as exc:
        logger.error("webhook_execution_failed", workflow_id=workflow.id, error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "execution_id": execution.id,
        "status": execution.status,
        "output_data": execution.output_data,
    }
