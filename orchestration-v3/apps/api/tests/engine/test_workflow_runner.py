"""워크플로우 러너 DAG 실행 단위 테스트 (ADR-0019).

DB·포트 없이 순수 노드(start·code·condition·end)만으로 선형 실행과 condition skip 전파를 검증한다.
async 러너는 asyncio.run으로 구동(프로젝트에 pytest-asyncio 미설치).
"""

import asyncio

from src.engine.workflow import (
    ExecutionCompleteEvent,
    ExecutionContext,
    NodeSkippedEvent,
    WorkflowRunner,
)


def _run(definition: dict, input_data: dict) -> list:
    async def _collect() -> list:
        ctx = ExecutionContext(execution_id="e1", input_data=input_data)
        return [ev async for ev in WorkflowRunner().run(definition, ctx, "e1")]

    return asyncio.run(_collect())


def test_linear_start_code_end():
    definition = {
        "nodes": [
            {"id": "start", "type": "start", "data": {"variables": [{"name": "x", "type": "number"}]}},
            {"id": "code", "type": "code", "data": {"code": "result = {'doubled': input_data['x'] * 2}"}},
            {"id": "end", "type": "end", "data": {"outputs": [{"name": "out", "value": "{{nodes.code.output.doubled}}"}]}},
        ],
        "edges": [
            {"source": "start", "target": "code"},
            {"source": "code", "target": "end"},
        ],
    }
    events = _run(definition, {"x": 5})
    completes = [e for e in events if isinstance(e, ExecutionCompleteEvent)]
    assert len(completes) == 1
    assert completes[0].output_data == {"out": 10}


def test_condition_skips_losing_branch():
    definition = {
        "nodes": [
            {"id": "start", "type": "start", "data": {}},
            {"id": "cond", "type": "condition", "data": {"left": "yes", "operator": "equals", "right": "no"}},
            {"id": "t", "type": "end", "data": {"outputs": [{"name": "r", "value": "true-branch"}]}},
            {"id": "f", "type": "end", "data": {"outputs": [{"name": "r", "value": "false-branch"}]}},
        ],
        "edges": [
            {"source": "start", "target": "cond"},
            {"source": "cond", "target": "t", "sourceHandle": "true"},
            {"source": "cond", "target": "f", "sourceHandle": "false"},
        ],
    }
    events = _run(definition, {})
    skipped = {e.node_id for e in events if isinstance(e, NodeSkippedEvent)}
    assert "t" in skipped  # 조건이 False → true 분기 skip
    completes = [e for e in events if isinstance(e, ExecutionCompleteEvent)]
    assert completes and completes[0].output_data == {"r": "false-branch"}
