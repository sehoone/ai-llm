"""Workflow execution engine — parallel DAG runner.

Responsibilities:
- Build a DAG from the workflow definition (nodes + edges)
- Execute independent nodes in parallel (asyncio.gather)
- Handle condition branching (skip unreachable branches)
- Persist execution state to DB (WorkflowExecution, NodeExecution)
- Emit SSE events via an asyncio.Queue for the streaming endpoint
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any, AsyncGenerator

from sqlmodel import Session

from src.common.logging import logger
from src.workflow.models.execution_model import ExecutionStatus, NodeExecution, WorkflowExecution
from src.workflow.models.workflow_model import Workflow
from src.workflow.schemas.execution_schema import (
    ExecutionCompleteEvent,
    ExecutionFailedEvent,
    NodeCompleteEvent,
    NodeFailedEvent,
    NodeSkippedEvent,
    NodeStartEvent,
)
from src.workflow.services.executor.context import ExecutionContext
from src.workflow.services.executor.registry import get_node

# Sentinel pushed to the queue when the execution is done
_DONE = object()


class WorkflowEngine:
    """Stateless engine — create a new instance per execution (or reuse; it holds no state)."""

    # ── Public API ────────────────────────────────────────────────────────────

    async def execute_stream(
        self,
        workflow: Workflow,
        input_data: dict[str, Any],
        user_id: int,
        db: Session,
    ) -> AsyncGenerator[str, None]:
        """Run a workflow and yield SSE-formatted event strings."""
        execution_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue()

        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow.id,
            user_id=user_id,
            status=ExecutionStatus.RUNNING,
            input_data=input_data,
        )
        db.add(execution)
        db.commit()

        task = asyncio.create_task(
            self._run(workflow, input_data, execution_id, db, queue)
        )

        try:
            while True:
                event = await queue.get()
                if event is _DONE:
                    break
                yield f"data: {event}\n\n"
        finally:
            if not task.done():
                task.cancel()

    async def execute(
        self,
        workflow: Workflow,
        input_data: dict[str, Any],
        user_id: int,
        db: Session,
    ) -> WorkflowExecution:
        """Run a workflow synchronously and return the completed execution record."""
        execution_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue()

        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow.id,
            user_id=user_id,
            status=ExecutionStatus.RUNNING,
            input_data=input_data,
        )
        db.add(execution)
        db.commit()

        await self._run(workflow, input_data, execution_id, db, queue)

        db.refresh(execution)
        return execution

    # ── Internal: parallel DAG runner ─────────────────────────────────────────

    async def _run(
        self,
        workflow: Workflow,
        input_data: dict[str, Any],
        execution_id: str,
        db: Session,
        queue: asyncio.Queue,
    ) -> None:
        execution = db.get(WorkflowExecution, execution_id)
        user_id = execution.user_id if execution else None
        ctx = ExecutionContext(execution_id=execution_id, input_data=input_data, user_id=user_id)

        try:
            definition = workflow.definition or {}
            nodes_def: list[dict] = definition.get("nodes", [])
            edges_def: list[dict] = definition.get("edges", [])

            nodes_by_id, adj, predecessors, condition_edges = self._build_structures(nodes_def, edges_def)

            completed: set[str] = set()  # successfully executed
            skipped: set[str] = set()    # skipped (condition branching)
            done: set[str] = set()       # completed | skipped
            final_output: dict[str, Any] = {}

            # ── helper: find nodes whose all predecessors are done ───────────
            def compute_ready() -> set[str]:
                return {
                    nid for nid in nodes_by_id
                    if nid not in done
                    and all(pred in done for pred in predecessors.get(nid, set()))
                }

            # ── helper: BFS-propagate skipped status + emit events ───────────
            async def propagate_skip(start_ids: set[str]) -> None:
                queue_bfs: deque[str] = deque(start_ids)
                while queue_bfs:
                    nid = queue_bfs.popleft()
                    if nid in done:
                        continue
                    skipped.add(nid)
                    done.add(nid)
                    await self._emit(queue, NodeSkippedEvent(node_id=nid).model_dump_json())
                    self._save_node_execution(
                        db, execution_id, nid,
                        nodes_by_id[nid]["type"],
                        ExecutionStatus.SKIPPED,
                        {}, None, None,
                    )
                    for succ in adj.get(nid, []):
                        queue_bfs.append(succ)

            # ── main execution loop ───────────────────────────────────────────
            ready = compute_ready()

            while ready:
                # Execute all ready nodes concurrently
                results = await asyncio.gather(
                    *[
                        self._execute_node(
                            node_id=nid,
                            node_def=nodes_by_id[nid],
                            ctx=ctx,
                            db=db,
                            event_queue=queue,
                            execution_id=execution_id,
                        )
                        for nid in ready
                    ],
                    return_exceptions=True,
                )

                newly_skipped: set[str] = set()

                for nid, result in zip(list(ready), results):
                    if isinstance(result, BaseException):
                        raise result

                    node_type: str
                    output: dict[str, Any]
                    node_type, output = result

                    completed.add(nid)
                    done.add(nid)

                    if node_type == "condition":
                        cond_result: bool = bool(output.get("result", False))
                        ctx.set_condition_result(nid, cond_result)
                        losing_handle = "false" if cond_result else "true"
                        for edge in condition_edges.get(nid, []):
                            if edge.get("sourceHandle") == losing_handle:
                                target = edge["target"]
                                if target not in done:
                                    newly_skipped.add(target)

                    if node_type == "end":
                        final_output = output

                if newly_skipped:
                    await propagate_skip(newly_skipped)

                ready = compute_ready()

            # All nodes processed — mark execution as done
            self._update_execution(db, execution_id, ExecutionStatus.COMPLETED, output_data=final_output)
            await self._emit(
                queue,
                ExecutionCompleteEvent(execution_id=execution_id, output_data=final_output).model_dump_json(),
            )
            logger.info("workflow_execution_completed", execution_id=execution_id)

        except Exception as exc:
            error_msg = str(exc)
            logger.error("workflow_execution_failed", execution_id=execution_id, error=error_msg)
            self._update_execution(db, execution_id, ExecutionStatus.FAILED, error=error_msg)
            await self._emit(
                queue,
                ExecutionFailedEvent(execution_id=execution_id, error=error_msg).model_dump_json(),
            )
        finally:
            await queue.put(_DONE)

    async def _execute_node(
        self,
        node_id: str,
        node_def: dict,
        ctx: ExecutionContext,
        db: Session,
        event_queue: asyncio.Queue,
        execution_id: str,
    ) -> tuple[str, dict[str, Any]]:
        """Execute a single node, persist state, and emit events.

        Returns (node_type, output_data).
        Raises on node failure (bubbles up to asyncio.gather).
        """
        node_type: str = node_def["type"]
        node_config: dict = node_def.get("data", {})
        resolved_inputs = ctx.resolve_node_inputs(node_config)

        await self._emit(
            event_queue,
            NodeStartEvent(node_id=node_id, node_type=node_type, input_data=resolved_inputs).model_dump_json(),
        )

        node_exec = NodeExecution(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            node_id=node_id,
            node_type=node_type,
            status=ExecutionStatus.RUNNING,
            input_data=resolved_inputs,
        )
        db.add(node_exec)
        db.commit()

        try:
            handler = get_node(node_type)
            output = await handler.execute(resolved_inputs, node_config, ctx)
            ctx.set_node_output(node_id, output)

            node_exec.status = ExecutionStatus.COMPLETED
            node_exec.output_data = output
            node_exec.completed_at = datetime.now(UTC)
            db.add(node_exec)
            db.commit()

            await self._emit(
                event_queue,
                NodeCompleteEvent(node_id=node_id, node_type=node_type, output_data=output).model_dump_json(),
            )
            return node_type, output

        except Exception as exc:
            error_msg = str(exc)
            logger.error(
                "node_execution_failed",
                node_id=node_id, node_type=node_type, error=error_msg, exc_info=True,
            )
            node_exec.status = ExecutionStatus.FAILED
            node_exec.error = error_msg
            node_exec.completed_at = datetime.now(UTC)
            db.add(node_exec)
            db.commit()

            await self._emit(
                event_queue,
                NodeFailedEvent(node_id=node_id, node_type=node_type, error=error_msg).model_dump_json(),
            )
            raise

    # ── DAG helpers ───────────────────────────────────────────────────────────

    def _build_structures(
        self,
        nodes_def: list[dict],
        edges_def: list[dict],
    ) -> tuple[
        dict[str, dict],        # nodes_by_id
        dict[str, list[str]],   # adj (src → [tgt])
        dict[str, set[str]],    # predecessors (nid → {src})
        dict[str, list[dict]],  # condition_edges (condition_nid → edges)
    ]:
        """Build adjacency, predecessor, and condition-edge structures.

        Also validates that the graph is acyclic (raises ValueError on cycles).
        """
        nodes_by_id: dict[str, dict] = {n["id"]: n for n in nodes_def}
        adj: dict[str, list[str]] = defaultdict(list)
        predecessors: dict[str, set[str]] = defaultdict(set)
        condition_edges: dict[str, list[dict]] = defaultdict(list)

        for edge in edges_def:
            src = edge["source"]
            tgt = edge["target"]
            adj[src].append(tgt)
            predecessors[tgt].add(src)
            if edge.get("sourceHandle") in ("true", "false"):
                condition_edges[src].append(edge)

        # Cycle detection via Kahn's algorithm
        in_degree = {nid: len(predecessors.get(nid, set())) for nid in nodes_by_id}
        q: deque[str] = deque(nid for nid, d in in_degree.items() if d == 0)
        visited = 0
        while q:
            nid = q.popleft()
            visited += 1
            for tgt in adj.get(nid, []):
                in_degree[tgt] -= 1
                if in_degree[tgt] == 0:
                    q.append(tgt)

        if visited != len(nodes_by_id):
            raise ValueError("Workflow definition contains a cycle — acyclic graphs only.")

        return dict(nodes_by_id), dict(adj), dict(predecessors), dict(condition_edges)

    # ── DB helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _update_execution(
        db: Session,
        execution_id: str,
        status: ExecutionStatus,
        output_data: dict | None = None,
        error: str | None = None,
    ) -> None:
        execution = db.get(WorkflowExecution, execution_id)
        if execution:
            execution.status = status
            execution.completed_at = datetime.now(UTC)
            if output_data is not None:
                execution.output_data = output_data
            if error is not None:
                execution.error = error
            db.add(execution)
            db.commit()

    @staticmethod
    def _save_node_execution(
        db: Session,
        execution_id: str,
        node_id: str,
        node_type: str,
        status: ExecutionStatus,
        input_data: dict,
        output_data: dict | None,
        error: str | None,
    ) -> None:
        now = datetime.now(UTC)
        node_exec = NodeExecution(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            node_id=node_id,
            node_type=node_type,
            status=status,
            input_data=input_data,
            output_data=output_data,
            error=error,
            completed_at=now,
        )
        db.add(node_exec)
        db.commit()

    # ── SSE helper ────────────────────────────────────────────────────────────

    @staticmethod
    async def _emit(queue: asyncio.Queue, payload: str) -> None:
        await queue.put(payload)


# Module-level singleton
workflow_engine = WorkflowEngine()
