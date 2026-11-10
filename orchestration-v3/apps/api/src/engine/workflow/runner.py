"""병렬 DAG 러너 (ADR-0019 §1). V2 engine._run 계승하되 **DB·SSE 미접촉**.

러너는 `ExecutionEvent` 객체를 async-generator로 흘린다 — 영속/직렬화는 도메인 서비스가 소비하며 수행.
선행이 모두 끝난 노드를 `asyncio.gather`로 병렬 실행하고, condition 분기의 패배 측은 BFS로 skip 전파한다.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import AsyncGenerator
from typing import Any

from src.engine.workflow.context import ExecutionContext
from src.engine.workflow.events import (
    ExecutionCompleteEvent,
    ExecutionEvent,
    ExecutionFailedEvent,
    NodeCompleteEvent,
    NodeFailedEvent,
    NodeSkippedEvent,
    NodeStartEvent,
)
from src.engine.workflow.planner import build_structures
from src.engine.workflow.registry import get_node

logger = logging.getLogger(__name__)

_DONE = object()  # 큐 종료 센티넬


class WorkflowRunner:
    """무상태 러너 — 실행마다 새 인스턴스여도 되고 재사용해도 된다(상태 없음)."""

    async def run(
        self, definition: dict[str, Any], ctx: ExecutionContext, execution_id: str
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """워크플로우를 실행하고 이벤트를 순차 yield. 완료 시 Execution(Complete|Failed)로 끝난다."""
        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(self._run(definition, ctx, execution_id, queue))
        try:
            while True:
                event = await queue.get()
                if event is _DONE:
                    break
                yield event
        finally:
            if not task.done():
                task.cancel()

    async def _run(
        self,
        definition: dict[str, Any],
        ctx: ExecutionContext,
        execution_id: str,
        queue: asyncio.Queue,
    ) -> None:
        try:
            nodes_def: list[dict] = definition.get("nodes", [])
            edges_def: list[dict] = definition.get("edges", [])
            g = build_structures(nodes_def, edges_def)

            done: set[str] = set()  # completed | skipped
            final_output: dict[str, Any] = {}

            def compute_ready() -> set[str]:
                return {
                    nid
                    for nid in g.nodes_by_id
                    if nid not in done and all(p in done for p in g.predecessors.get(nid, set()))
                }

            async def propagate_skip(start_ids: set[str]) -> None:
                bfs: deque[str] = deque(start_ids)
                while bfs:
                    nid = bfs.popleft()
                    if nid in done:
                        continue
                    done.add(nid)
                    await queue.put(
                        NodeSkippedEvent(node_id=nid, node_type=g.nodes_by_id[nid]["type"])
                    )
                    for succ in g.adjacency.get(nid, []):
                        bfs.append(succ)

            ready = compute_ready()
            while ready:
                results = await asyncio.gather(
                    *[self._execute_node(nid, g.nodes_by_id[nid], ctx, queue) for nid in ready],
                    return_exceptions=True,
                )

                newly_skipped: set[str] = set()
                for nid, result in zip(list(ready), results):
                    if isinstance(result, BaseException):
                        raise result
                    node_type, output = result
                    done.add(nid)

                    if node_type == "condition":
                        cond_result = bool(output.get("result", False))
                        ctx.set_condition_result(nid, cond_result)
                        losing_handle = "false" if cond_result else "true"
                        for edge in g.condition_edges.get(nid, []):
                            if edge.get("sourceHandle") == losing_handle:
                                target = edge["target"]
                                if target not in done:
                                    newly_skipped.add(target)

                    if node_type == "end":
                        final_output = output

                if newly_skipped:
                    await propagate_skip(newly_skipped)
                ready = compute_ready()

            await queue.put(
                ExecutionCompleteEvent(execution_id=execution_id, output_data=final_output)
            )
            logger.info("workflow_execution_completed execution_id=%s", execution_id)

        except Exception as exc:  # noqa: BLE001 — 이벤트로 실패 통지 후 종료
            logger.error("workflow_execution_failed execution_id=%s error=%s", execution_id, exc)
            await queue.put(ExecutionFailedEvent(execution_id=execution_id, error=str(exc)))
        finally:
            await queue.put(_DONE)

    async def _execute_node(
        self, node_id: str, node_def: dict, ctx: ExecutionContext, queue: asyncio.Queue
    ) -> tuple[str, dict[str, Any]]:
        """단일 노드 실행 + 이벤트 emit. (node_type, output) 반환. 실패 시 raise(gather로 전파)."""
        node_type: str = node_def["type"]
        node_config: dict = node_def.get("data", {})
        resolved_inputs = ctx.resolve_node_inputs(node_config)

        await queue.put(
            NodeStartEvent(node_id=node_id, node_type=node_type, input_data=resolved_inputs)
        )
        try:
            handler = get_node(node_type)
            output = await handler.execute(resolved_inputs, node_config, ctx)
            ctx.set_node_output(node_id, output)
            await queue.put(
                NodeCompleteEvent(node_id=node_id, node_type=node_type, output_data=output)
            )
            return node_type, output
        except Exception as exc:
            logger.exception("node_execution_failed node_id=%s node_type=%s", node_id, node_type)
            await queue.put(
                NodeFailedEvent(node_id=node_id, node_type=node_type, error=str(exc))
            )
            raise
