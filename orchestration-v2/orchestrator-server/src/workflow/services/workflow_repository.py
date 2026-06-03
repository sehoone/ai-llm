"""Repository mixin for Workflow, Execution, Schedule, and Endpoint DB operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session, select

from src.workflow.models.endpoint_model import WorkflowEndpoint
from src.workflow.models.execution_model import NodeExecution, WorkflowExecution
from src.workflow.models.schedule_model import WorkflowSchedule
from src.workflow.models.workflow_model import Workflow


class WorkflowRepositoryMixin:
    """Mixin that adds workflow/execution query methods to DatabaseService."""

    engine: object  # provided by DatabaseService

    # ── Workflow CRUD ─────────────────────────────────────────────────────────

    def create_workflow(self, db: Session, user_id: int, name: str, description: str, definition: dict) -> Workflow:
        workflow = Workflow(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            definition=definition,
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return workflow

    def get_workflow(self, db: Session, workflow_id: str) -> Optional[Workflow]:
        return db.get(Workflow, workflow_id)

    def list_workflows(self, db: Session, user_id: int, limit: int = 50, offset: int = 0) -> list[Workflow]:
        stmt = (
            select(Workflow)
            .where(Workflow.user_id == user_id)
            .order_by(Workflow.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.exec(stmt).all())

    def update_workflow(self, db: Session, workflow: Workflow, **fields) -> Workflow:
        for key, value in fields.items():
            if value is not None:
                setattr(workflow, key, value)
        workflow.updated_at = datetime.now(UTC)
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return workflow

    def delete_workflow(self, db: Session, workflow: Workflow) -> None:
        db.delete(workflow)
        db.commit()

    # ── Execution queries ─────────────────────────────────────────────────────

    def get_execution(self, db: Session, execution_id: str) -> Optional[WorkflowExecution]:
        return db.get(WorkflowExecution, execution_id)

    def list_executions(
        self, db: Session, workflow_id: str, limit: int = 20, offset: int = 0
    ) -> list[WorkflowExecution]:
        stmt = (
            select(WorkflowExecution)
            .where(WorkflowExecution.workflow_id == workflow_id)
            .order_by(WorkflowExecution.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.exec(stmt).all())

    def list_node_executions(self, db: Session, execution_id: str) -> list[NodeExecution]:
        stmt = (
            select(NodeExecution)
            .where(NodeExecution.execution_id == execution_id)
            .order_by(NodeExecution.created_at.asc())
        )
        return list(db.exec(stmt).all())

    # ── Webhook ───────────────────────────────────────────────────────────────

    def get_workflow_by_token(self, db: Session, token: str) -> Optional[Workflow]:
        stmt = select(Workflow).where(Workflow.webhook_token == token)
        return db.exec(stmt).first()

    # ── Schedule CRUD ─────────────────────────────────────────────────────────

    def create_schedule(
        self,
        db: Session,
        workflow_id: str,
        user_id: int,
        label: str,
        cron_expr: str,
        input_data: dict,
    ) -> WorkflowSchedule:
        schedule = WorkflowSchedule(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_id=user_id,
            label=label,
            cron_expr=cron_expr,
            input_data=input_data,
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    def get_schedule(self, db: Session, schedule_id: str) -> Optional[WorkflowSchedule]:
        return db.get(WorkflowSchedule, schedule_id)

    def list_schedules(self, db: Session, workflow_id: str) -> list[WorkflowSchedule]:
        stmt = (
            select(WorkflowSchedule)
            .where(WorkflowSchedule.workflow_id == workflow_id)
            .order_by(WorkflowSchedule.created_at.desc())
        )
        return list(db.exec(stmt).all())

    def list_all_active_schedules(self, db: Session) -> list[WorkflowSchedule]:
        """Used by scheduler on startup to reload all jobs."""
        stmt = select(WorkflowSchedule).where(WorkflowSchedule.is_active == True)  # noqa: E712
        return list(db.exec(stmt).all())

    def update_schedule(self, db: Session, schedule: WorkflowSchedule, **fields) -> WorkflowSchedule:
        for key, value in fields.items():
            setattr(schedule, key, value)
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    def delete_schedule(self, db: Session, schedule: WorkflowSchedule) -> None:
        db.delete(schedule)
        db.commit()

    # ── Endpoint CRUD ─────────────────────────────────────────────────────────

    def create_endpoint(
        self,
        db: Session,
        workflow_id: str,
        user_id: int,
        path: str,
        method: str,
        description: str,
        is_active: bool = True,
    ) -> WorkflowEndpoint:
        endpoint = WorkflowEndpoint(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_id=user_id,
            path=path,
            method=method,
            description=description,
            is_active=is_active,
        )
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)
        return endpoint

    def get_endpoint(self, db: Session, endpoint_id: str) -> Optional[WorkflowEndpoint]:
        return db.get(WorkflowEndpoint, endpoint_id)

    def get_endpoint_by_path(self, db: Session, path: str, method: str) -> Optional[WorkflowEndpoint]:
        stmt = (
            select(WorkflowEndpoint)
            .where(WorkflowEndpoint.path == path)
            .where(WorkflowEndpoint.method == method)
            .where(WorkflowEndpoint.is_active == True)  # noqa: E712
        )
        return db.exec(stmt).first()

    def list_endpoints(self, db: Session, workflow_id: str) -> list[WorkflowEndpoint]:
        stmt = (
            select(WorkflowEndpoint)
            .where(WorkflowEndpoint.workflow_id == workflow_id)
            .order_by(WorkflowEndpoint.created_at.desc())
        )
        return list(db.exec(stmt).all())

    def update_endpoint(self, db: Session, endpoint: WorkflowEndpoint, **fields) -> WorkflowEndpoint:
        for key, value in fields.items():
            if value is not None:
                setattr(endpoint, key, value)
        endpoint.updated_at = datetime.now(UTC)
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)
        return endpoint

    def delete_endpoint(self, db: Session, endpoint: WorkflowEndpoint) -> None:
        db.delete(endpoint)
        db.commit()
