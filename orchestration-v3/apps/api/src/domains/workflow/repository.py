"""workflow 도메인 영속 계층 (llmonl). 5개 테이블 CRUD. FK 없이 명시 정리."""

from __future__ import annotations

from sqlmodel import Session, col, select

from src.domains.workflow.model import (
    NodeExecution,
    Workflow,
    WorkflowEndpoint,
    WorkflowExecution,
    WorkflowSchedule,
)


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Workflow ──
    def create(self, w: Workflow) -> Workflow:
        self.session.add(w)
        self.session.commit()
        self.session.refresh(w)
        return w

    def get(self, workflow_id: str) -> Workflow | None:
        return self.session.get(Workflow, workflow_id)

    def get_by_webhook_token(self, token: str) -> Workflow | None:
        return self.session.exec(
            select(Workflow).where(Workflow.webhook_token == token)
        ).first()

    def list(self, user_id: int, limit: int = 50, offset: int = 0) -> list[Workflow]:
        return list(
            self.session.exec(
                select(Workflow)
                .where(Workflow.user_id == user_id)
                .order_by(col(Workflow.created_at).desc())
                .limit(limit)
                .offset(offset)
            ).all()
        )

    def save(self, w: Workflow) -> Workflow:
        self.session.add(w)
        self.session.commit()
        self.session.refresh(w)
        return w

    def delete(self, w: Workflow) -> None:
        """워크플로우 + 종속(실행·노드실행·스케줄·엔드포인트) 명시 정리."""
        for e in self.list_executions(w.id):
            self._delete_node_executions(e.id)
            self.session.delete(e)
        for s in self.list_schedules(w.id):
            self.session.delete(s)
        for ep in self.list_endpoints(w.id):
            self.session.delete(ep)
        self.session.delete(w)
        self.session.commit()

    # ── Execution ──
    def create_execution(self, e: WorkflowExecution) -> WorkflowExecution:
        self.session.add(e)
        self.session.commit()
        self.session.refresh(e)
        return e

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return self.session.get(WorkflowExecution, execution_id)

    def save_execution(self, e: WorkflowExecution) -> WorkflowExecution:
        self.session.add(e)
        self.session.commit()
        self.session.refresh(e)
        return e

    def list_executions(self, workflow_id: str, limit: int = 50) -> list[WorkflowExecution]:
        return list(
            self.session.exec(
                select(WorkflowExecution)
                .where(WorkflowExecution.workflow_id == workflow_id)
                .order_by(col(WorkflowExecution.created_at).desc())
                .limit(limit)
            ).all()
        )

    # ── NodeExecution ──
    def create_node_execution(self, n: NodeExecution) -> NodeExecution:
        self.session.add(n)
        self.session.commit()
        self.session.refresh(n)
        return n

    def save_node_execution(self, n: NodeExecution) -> NodeExecution:
        self.session.add(n)
        self.session.commit()
        self.session.refresh(n)
        return n

    def list_node_executions(self, execution_id: str) -> list[NodeExecution]:
        return list(
            self.session.exec(
                select(NodeExecution)
                .where(NodeExecution.execution_id == execution_id)
                .order_by(col(NodeExecution.created_at).asc())
            ).all()
        )

    def _delete_node_executions(self, execution_id: str) -> None:
        for n in self.list_node_executions(execution_id):
            self.session.delete(n)

    # ── Schedule ──
    def create_schedule(self, s: WorkflowSchedule) -> WorkflowSchedule:
        self.session.add(s)
        self.session.commit()
        self.session.refresh(s)
        return s

    def get_schedule(self, schedule_id: str) -> WorkflowSchedule | None:
        return self.session.get(WorkflowSchedule, schedule_id)

    def save_schedule(self, s: WorkflowSchedule) -> WorkflowSchedule:
        self.session.add(s)
        self.session.commit()
        self.session.refresh(s)
        return s

    def delete_schedule(self, s: WorkflowSchedule) -> None:
        self.session.delete(s)
        self.session.commit()

    def list_schedules(self, workflow_id: str) -> list[WorkflowSchedule]:
        return list(
            self.session.exec(
                select(WorkflowSchedule)
                .where(WorkflowSchedule.workflow_id == workflow_id)
                .order_by(col(WorkflowSchedule.created_at).desc())
            ).all()
        )

    def list_active_schedules(self) -> list[WorkflowSchedule]:
        return list(
            self.session.exec(
                select(WorkflowSchedule).where(WorkflowSchedule.is_active == True)  # noqa: E712
            ).all()
        )

    # ── Endpoint ──
    def create_endpoint(self, e: WorkflowEndpoint) -> WorkflowEndpoint:
        self.session.add(e)
        self.session.commit()
        self.session.refresh(e)
        return e

    def get_endpoint(self, endpoint_id: str) -> WorkflowEndpoint | None:
        return self.session.get(WorkflowEndpoint, endpoint_id)

    def get_endpoint_by_route(self, path: str, method: str) -> WorkflowEndpoint | None:
        return self.session.exec(
            select(WorkflowEndpoint)
            .where(WorkflowEndpoint.path == path)
            .where(WorkflowEndpoint.method == method.upper())
        ).first()

    def save_endpoint(self, e: WorkflowEndpoint) -> WorkflowEndpoint:
        self.session.add(e)
        self.session.commit()
        self.session.refresh(e)
        return e

    def delete_endpoint(self, e: WorkflowEndpoint) -> None:
        self.session.delete(e)
        self.session.commit()

    def list_endpoints(self, workflow_id: str) -> list[WorkflowEndpoint]:
        return list(
            self.session.exec(
                select(WorkflowEndpoint)
                .where(WorkflowEndpoint.workflow_id == workflow_id)
                .order_by(col(WorkflowEndpoint.created_at).desc())
            ).all()
        )
