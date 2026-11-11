"""workflow 도메인 서비스 — 경계·인가·영속·트리거 오케스트레이션 (ADR-0019).

도메인 책임(ADR-0005): HTTP 경계·인가·관계형 영속. 실행 능력은 `engine/workflow`에 위임한다.
- **러너 이벤트 소비자**: `WorkflowRunner`를 돌리며 각 `ExecutionEvent`로 ① 실행/노드 행 영속,
  ② SSE 직렬화(스트림). engine은 DB·SSE를 모른다.
- **포트 주입**: rag 검색은 `domains/rag` 호출 콜백, LLM은 `llm_resource`→`LlmConfig` 값으로 주입
  (engine→domains import 없음 — ADR-0019 §2).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlmodel import Session

from src.core.config import settings
from src.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
    ValidationError,
)
from src.domains.workflow.model import (
    ExecutionStatus,
    NodeExecution,
    Workflow,
    WorkflowEndpoint,
    WorkflowExecution,
    WorkflowSchedule,
)
from src.domains.workflow.repository import WorkflowRepository
from src.domains.workflow.scheduler import workflow_scheduler
from src.domains.workflow.schema import (
    EndpointCreateRequest,
    EndpointUpdateRequest,
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
)
from src.engine.llm.config import LlmConfig
from src.engine.workflow import (
    ExecutionCompleteEvent,
    ExecutionContext,
    ExecutionEvent,
    ExecutionFailedEvent,
    NodeCompleteEvent,
    NodeFailedEvent,
    NodeSkippedEvent,
    NodeStartEvent,
    WorkflowRunner,
    list_node_types,
)
from src.platform.llm_resource.model import LlmResource
from src.platform.llm_resource.repository import LlmResourceRepository
from src.platform.user.model import User, UserRole

logger = logging.getLogger(__name__)

_ADMIN_ROLES = (UserRole.ADMIN, UserRole.SUPERADMIN)


def _config_from_resource(r: LlmResource) -> LlmConfig:
    """llm_resource 행 → LlmConfig (chat/gpts 도메인과 동일 규칙)."""
    model = r.deployment_name if r.provider == "azure" else (r.model_name or r.name)
    return LlmConfig(
        provider=r.provider,
        model=model or r.name,
        api_key=r.api_key or None,
        api_base=r.api_base or None,
        api_version=r.api_version or None,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens or None,
    )


def _sse(event: ExecutionEvent) -> str:
    """러너 이벤트 → web `createSSEProgressHandler`가 파싱하는 `data: {json}\\n\\n` 프레임."""
    return f"data: {event.model_dump_json()}\n\n"


def _now() -> datetime:
    return datetime.utcnow()


class WorkflowService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = WorkflowRepository(session)

    # ── 인가 ──
    def _owned(self, workflow_id: str, user: User) -> Workflow:
        w = self.repo.get(workflow_id)
        if w is None:
            raise NotFoundError("Workflow not found")
        if w.user_id != user.id and user.role not in _ADMIN_ROLES:
            raise PermissionDeniedError("Workflow not found or access denied")
        return w

    # ── Workflow CRUD ──
    def create(self, user: User, req: WorkflowCreateRequest) -> Workflow:
        w = Workflow(
            user_id=user.id,
            name=req.name,
            description=req.description,
            definition=req.definition.model_dump(),
        )
        return self.repo.create(w)

    def list(self, user: User, limit: int, offset: int) -> list[Workflow]:
        return self.repo.list(user.id, limit, offset)

    def get(self, workflow_id: str, user: User) -> Workflow:
        return self._owned(workflow_id, user)

    def update(self, workflow_id: str, user: User, req: WorkflowUpdateRequest) -> Workflow:
        w = self._owned(workflow_id, user)
        data = req.model_dump(exclude_unset=True)
        if "definition" in data and req.definition is not None:
            data["definition"] = req.definition.model_dump()
        for key, value in data.items():
            setattr(w, key, value)
        w.updated_at = _now()
        return self.repo.save(w)

    def delete(self, workflow_id: str, user: User) -> None:
        w = self._owned(workflow_id, user)
        for s in self.repo.list_schedules(w.id):
            workflow_scheduler.remove_job(s.id)
        self.repo.delete(w)

    def toggle_publish(self, workflow_id: str, user: User) -> Workflow:
        w = self._owned(workflow_id, user)
        w.is_published = not w.is_published
        w.updated_at = _now()
        return self.repo.save(w)

    # ── 노드 팔레트 ──
    def node_types(self) -> list[dict]:
        return list_node_types()

    # ── 실행 컨텍스트 (포트 주입) ──
    def _llm_config_resolver(self):
        """노드가 선택한 llm_resource_id → LlmConfig. 무효/미지정이면 기본 chat 리소스로 폴백.

        web llm 노드가 `llm_resource_id`(chat-models 드롭다운 선택)를 node.data에 담아 보낸다
        (ADR-0019 §4 후속 — model 문자열 → llm_resource_id 재매핑). engine은 이 콜백만 호출한다.
        """
        repo = LlmResourceRepository(self.session)

        def resolve(resource_id: int | None) -> LlmConfig | None:
            if resource_id is not None:
                r = repo.get(resource_id)
                if r is not None and r.is_active and r.resource_type == "chat":
                    return _config_from_resource(r)
            default = repo.default_chat_model()
            return _config_from_resource(default) if default is not None else None

        return resolve

    def _build_context(
        self, execution_id: str, input_data: dict[str, Any], user_id: int
    ) -> ExecutionContext:
        async def _rag_search(*, query: str, rag_group: str, limit: int) -> list[dict]:
            def _search() -> list[dict]:
                from src.core.db import engine as db_engine
                from src.domains.rag import RagService, SearchRequest

                with Session(db_engine) as s:
                    user = s.get(User, user_id)
                    if user is None:
                        return []
                    try:
                        return RagService(s).search(
                            user, SearchRequest(rag_group=rag_group, query=query, limit=limit)
                        )
                    except Exception:
                        logger.exception("workflow_rag_search_failed")
                        return []

            return await asyncio.to_thread(_search)

        resolver = self._llm_config_resolver()
        return ExecutionContext(
            execution_id=execution_id,
            input_data=input_data,
            user_id=user_id,
            rag_search=_rag_search,
            llm_config=resolver(None),  # 기본 chat 리소스(폴백)
            llm_config_resolver=resolver,
        )

    # ── 러너 구동 + 영속 ──
    async def _run_and_persist(
        self, workflow: Workflow, execution: WorkflowExecution, user_id: int
    ) -> AsyncGenerator[ExecutionEvent, None]:
        ctx = self._build_context(execution.id, execution.input_data or {}, user_id)
        node_rows: dict[str, NodeExecution] = {}
        async for event in WorkflowRunner().run(workflow.definition or {}, ctx, execution.id):
            self._persist_event(execution, node_rows, event)
            yield event

    def _persist_event(
        self,
        execution: WorkflowExecution,
        node_rows: dict[str, NodeExecution],
        event: ExecutionEvent,
    ) -> None:
        if isinstance(event, NodeStartEvent):
            row = NodeExecution(
                execution_id=execution.id,
                node_id=event.node_id,
                node_type=event.node_type,
                status=ExecutionStatus.RUNNING,
                input_data=event.input_data,
            )
            self.repo.create_node_execution(row)
            node_rows[event.node_id] = row
        elif isinstance(event, NodeCompleteEvent):
            row = node_rows.get(event.node_id)
            if row is not None:
                row.status = ExecutionStatus.COMPLETED
                row.output_data = event.output_data
                row.completed_at = _now()
                self.repo.save_node_execution(row)
        elif isinstance(event, NodeFailedEvent):
            row = node_rows.get(event.node_id)
            if row is not None:
                row.status = ExecutionStatus.FAILED
                row.error = event.error
                row.completed_at = _now()
                self.repo.save_node_execution(row)
        elif isinstance(event, NodeSkippedEvent):
            self.repo.create_node_execution(
                NodeExecution(
                    execution_id=execution.id,
                    node_id=event.node_id,
                    node_type=event.node_type,
                    status=ExecutionStatus.SKIPPED,
                    completed_at=_now(),
                )
            )
        elif isinstance(event, ExecutionCompleteEvent):
            execution.status = ExecutionStatus.COMPLETED
            execution.output_data = event.output_data
            execution.completed_at = _now()
            self.repo.save_execution(execution)
        elif isinstance(event, ExecutionFailedEvent):
            execution.status = ExecutionStatus.FAILED
            execution.error = event.error
            execution.completed_at = _now()
            self.repo.save_execution(execution)

    # ── 실행 (동기 / SSE) ──
    async def execute(
        self, workflow: Workflow, input_data: dict[str, Any], user_id: int
    ) -> WorkflowExecution:
        execution = self.repo.create_execution(
            WorkflowExecution(
                workflow_id=workflow.id,
                user_id=user_id,
                status=ExecutionStatus.RUNNING,
                input_data=input_data,
            )
        )
        async for _event in self._run_and_persist(workflow, execution, user_id):
            pass
        self.session.refresh(execution)
        return execution

    async def execute_stream(
        self, workflow: Workflow, input_data: dict[str, Any], user_id: int
    ) -> AsyncGenerator[str, None]:
        execution = self.repo.create_execution(
            WorkflowExecution(
                workflow_id=workflow.id,
                user_id=user_id,
                status=ExecutionStatus.RUNNING,
                input_data=input_data,
            )
        )
        async for event in self._run_and_persist(workflow, execution, user_id):
            yield _sse(event)

    def node_executions(self, execution_id: str) -> list[NodeExecution]:
        return self.repo.list_node_executions(execution_id)

    # ── 실행 조회 ──
    def get_execution(self, execution_id: str, user: User) -> WorkflowExecution:
        e = self.repo.get_execution(execution_id)
        if e is None:
            raise NotFoundError("Execution not found")
        if e.user_id != user.id and user.role not in _ADMIN_ROLES:
            raise PermissionDeniedError("Access denied")
        return e

    def list_executions(self, workflow_id: str, user: User) -> list[WorkflowExecution]:
        self._owned(workflow_id, user)
        return self.repo.list_executions(workflow_id)

    # ── 웹훅 ──
    def manage_webhook(self, workflow_id: str, user: User, action: str) -> str | None:
        w = self._owned(workflow_id, user)
        if action == "generate":
            w.webhook_token = uuid.uuid4().hex
        elif action == "revoke":
            w.webhook_token = None
        else:
            raise ValidationError("action must be 'generate' or 'revoke'")
        w.updated_at = _now()
        self.repo.save(w)
        return w.webhook_token

    # ── 스케줄 ──
    def list_schedules(self, workflow_id: str, user: User) -> list[WorkflowSchedule]:
        self._owned(workflow_id, user)
        return self.repo.list_schedules(workflow_id)

    def create_schedule(
        self, workflow_id: str, user: User, req: ScheduleCreateRequest
    ) -> WorkflowSchedule:
        self._owned(workflow_id, user)
        s = WorkflowSchedule(
            workflow_id=workflow_id,
            user_id=user.id,
            label=req.label,
            cron_expr=req.cron_expr,
            input_data=req.input_data,
        )
        s = self.repo.create_schedule(s)
        if s.is_active:
            workflow_scheduler.add_job(s.id, s.cron_expr)
        return s

    def update_schedule(
        self, workflow_id: str, schedule_id: str, user: User, req: ScheduleUpdateRequest
    ) -> WorkflowSchedule:
        self._owned(workflow_id, user)
        s = self.repo.get_schedule(schedule_id)
        if s is None or s.workflow_id != workflow_id:
            raise NotFoundError("Schedule not found")
        for key, value in req.model_dump(exclude_unset=True).items():
            setattr(s, key, value)
        s = self.repo.save_schedule(s)
        # 변경된 cron/활성상태를 job에 반영
        workflow_scheduler.remove_job(s.id)
        if s.is_active:
            workflow_scheduler.add_job(s.id, s.cron_expr)
        return s

    def delete_schedule(self, workflow_id: str, schedule_id: str, user: User) -> None:
        self._owned(workflow_id, user)
        s = self.repo.get_schedule(schedule_id)
        if s is None or s.workflow_id != workflow_id:
            raise NotFoundError("Schedule not found")
        workflow_scheduler.remove_job(s.id)
        self.repo.delete_schedule(s)

    # ── 동적 엔드포인트 ──
    def list_endpoints(self, workflow_id: str, user: User) -> list[WorkflowEndpoint]:
        self._owned(workflow_id, user)
        return self.repo.list_endpoints(workflow_id)

    def create_endpoint(
        self, workflow_id: str, user: User, req: EndpointCreateRequest
    ) -> WorkflowEndpoint:
        self._owned(workflow_id, user)
        path = req.path.strip("/")
        if self.repo.get_endpoint_by_route(path, req.method) is not None:
            raise ConflictError("Endpoint (path, method) already exists")
        e = WorkflowEndpoint(
            workflow_id=workflow_id,
            user_id=user.id,
            path=path,
            method=req.method.upper(),
            description=req.description,
            is_active=req.is_active,
        )
        return self.repo.create_endpoint(e)

    def update_endpoint(
        self, workflow_id: str, endpoint_id: str, user: User, req: EndpointUpdateRequest
    ) -> WorkflowEndpoint:
        self._owned(workflow_id, user)
        e = self.repo.get_endpoint(endpoint_id)
        if e is None or e.workflow_id != workflow_id:
            raise NotFoundError("Endpoint not found")
        data = req.model_dump(exclude_unset=True)
        if "path" in data and data["path"] is not None:
            data["path"] = data["path"].strip("/")
        if "method" in data and data["method"] is not None:
            data["method"] = data["method"].upper()
        for key, value in data.items():
            setattr(e, key, value)
        e.updated_at = _now()
        return self.repo.save_endpoint(e)

    def delete_endpoint(self, workflow_id: str, endpoint_id: str, user: User) -> None:
        self._owned(workflow_id, user)
        e = self.repo.get_endpoint(endpoint_id)
        if e is None or e.workflow_id != workflow_id:
            raise NotFoundError("Endpoint not found")
        self.repo.delete_endpoint(e)

    # ── 공개 트리거 (웹훅 / 동적 엔드포인트) ──
    async def trigger_by_webhook(self, token: str, input_data: dict[str, Any]) -> WorkflowExecution:
        w = self.repo.get_by_webhook_token(token)
        if w is None:
            raise NotFoundError("Unknown webhook token")
        return await self.execute(w, input_data, w.user_id)

    async def trigger_by_endpoint(
        self,
        path: str,
        method: str,
        input_data: dict[str, Any],
        caller: User | None,
    ) -> WorkflowExecution:
        endpoint = self.repo.get_endpoint_by_route(path.strip("/"), method)
        if endpoint is None or not endpoint.is_active:
            raise NotFoundError("No workflow bound to this route")
        w = self.repo.get(endpoint.workflow_id)
        if w is None:
            raise NotFoundError("Bound workflow not found")
        # 미발행 워크플로우는 인증 필요(ADR-0019 보안). 발행 워크플로우는 공개.
        if not w.is_published and caller is None:
            raise UnauthorizedError("Authentication required (unpublished)")
        return await self.execute(w, input_data, w.user_id)


# 트리거 바디 방어 (dict가 아닌 입력 정규화)
def coerce_input(body: Any) -> dict[str, Any]:
    if isinstance(body, dict):
        return body
    try:
        parsed = json.loads(body) if isinstance(body, (str, bytes)) else {}
    except (json.JSONDecodeError, TypeError):
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}
