"""샘플 06 — 워크플로우 엔진 API

Routes:
    GET  /api/v1/sample/workflow/node-types      — 사용 가능한 노드 타입 목록
    POST /api/v1/sample/workflow/run             — 워크플로우 실행 (전체 결과)
    POST /api/v1/sample/workflow/run/stream      — 워크플로우 실행 (SSE 스트리밍)
    GET  /api/v1/sample/workflow/presets         — 예시 워크플로우 정의 목록

학습 포인트:
    1. DAG: 의존성 기반 병렬 실행 (asyncio.gather)
    2. 노드 타입 레지스트리: @register_node 데코레이터로 확장 가능
    3. SSE 이벤트 큐: 실행 중 상태를 실시간으로 클라이언트에 전달
    4. 실제 프로젝트에서는 DB에 WorkflowExecution + NodeExecution 기록

실제 구현 코드:
    src/workflow/services/executor/engine.py
    src/workflow/api/workflow_api.py
    src/workflow/api/execution_api.py
"""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .engine import (
    NodeDefinition,
    WorkflowDefinition,
    WorkflowEngine,
    _NODE_REGISTRY,
)

router = APIRouter()
engine = WorkflowEngine()


# ── 스키마 ──────────────────────────────────────────────────────────────────────

class NodeDef(BaseModel):
    id: str
    node_type: str
    config: dict
    dependencies: list[str] = []


class WorkflowRunRequest(BaseModel):
    name: str = "샘플 워크플로우"
    nodes: list[NodeDef]
    input: dict = {}


# ── 사전 정의 워크플로우 ───────────────────────────────────────────────────────

PRESETS = {
    "simple_chain": {
        "name": "단순 순차 실행",
        "description": "start → process → end 순서로 실행",
        "nodes": [
            {"id": "start", "node_type": "echo", "config": {"message": "워크플로우 시작"}, "dependencies": []},
            {"id": "process", "node_type": "echo", "config": {"message": "데이터 처리 중"}, "dependencies": ["start"]},
            {"id": "end", "node_type": "echo", "config": {"message": "완료"}, "dependencies": ["process"]},
        ],
    },
    "parallel_fan_out": {
        "name": "병렬 팬아웃",
        "description": "start 이후 A, B, C가 동시 실행 → merge에서 합산",
        "nodes": [
            {"id": "start", "node_type": "echo", "config": {"message": "시작"}, "dependencies": []},
            {"id": "task_a", "node_type": "echo", "config": {"message": "태스크 A"}, "dependencies": ["start"]},
            {"id": "task_b", "node_type": "echo", "config": {"message": "태스크 B"}, "dependencies": ["start"]},
            {"id": "task_c", "node_type": "echo", "config": {"message": "태스크 C"}, "dependencies": ["start"]},
            {"id": "merge", "node_type": "code",
             "config": {"code": "result = f'A+B+C 결과 통합: {context[\"task_a\"]}, {context[\"task_b\"]}, {context[\"task_c\"]}'"},
             "dependencies": ["task_a", "task_b", "task_c"]},
        ],
    },
    "llm_chain": {
        "name": "LLM 체인",
        "description": "에코 전처리 → LLM 분석 → 결과 포맷팅",
        "nodes": [
            {"id": "prepare", "node_type": "echo", "config": {"message": "데이터 준비 완료"}, "dependencies": []},
            {"id": "analyze", "node_type": "llm",
             "config": {"prompt": "이전 단계 결과를 바탕으로 인사이트를 제공해주세요"},
             "dependencies": ["prepare"]},
            {"id": "format", "node_type": "code",
             "config": {"code": "result = {'summary': context.get('analyze', ''), 'status': 'done'}"},
             "dependencies": ["analyze"]},
        ],
    },
}


# ── 엔드포인트 ──────────────────────────────────────────────────────────────────

@router.get(
    "/node-types",
    summary="사용 가능한 노드 타입",
    description="""
등록된 워크플로우 노드 타입 목록을 반환합니다.

새 노드 타입 추가 방법 (`src/workflow/services/executor/nodes/` 참고):
```python
from src.sample._06_workflow_engine.engine import register_node

@register_node("my_custom_node")
async def my_node(config: dict, context: dict) -> str:
    return f"처리 결과: {config['param']}"
```

**실제 노드 타입:** `src/workflow/services/executor/registry.py`
    """,
)
async def get_node_types():
    return {
        "node_types": list(_NODE_REGISTRY.keys()),
        "descriptions": {
            "echo": "메시지를 그대로 반환 (테스트/디버그용)",
            "llm": "LangGraphAgent를 통한 LLM 호출",
            "http": "외부 HTTP API 호출 (aiohttp)",
            "code": "Python 코드 실행 (context 변수 접근 가능)",
            "condition": "조건 분기 — true/false 브랜치 선택",
        },
    }


@router.get(
    "/presets",
    summary="예시 워크플로우 정의",
    description="미리 정의된 워크플로우 예시 목록. /run 에 그대로 전달하여 테스트 가능.",
)
async def get_presets():
    return {
        "presets": {
            key: {
                "name": val["name"],
                "description": val["description"],
                "nodes": val["nodes"],
            }
            for key, val in PRESETS.items()
        },
        "usage": "POST /api/v1/sample/workflow/run 에 nodes 배열을 전달하세요.",
    }


@router.post(
    "/run",
    summary="워크플로우 실행 (전체 결과)",
    description="""
DAG 워크플로우를 실행하고 모든 노드 결과를 반환합니다.

**병렬 실행 예시 (parallel_fan_out 프리셋):**
- `start` 완료 → `task_a`, `task_b`, `task_c` **동시 실행** (asyncio.gather)
- 셋 다 완료 → `merge` 실행

**실제 구현 코드:** `src/workflow/services/executor/engine.py`

**팁:** `/presets` 에서 예시 workflows를 확인하세요.
    """,
)
async def run_workflow(body: WorkflowRunRequest):
    import uuid

    workflow = WorkflowDefinition(
        id=str(uuid.uuid4()),
        name=body.name,
        nodes=[
            NodeDefinition(
                id=n.id,
                node_type=n.node_type,
                config=n.config,
                dependencies=n.dependencies,
            )
            for n in body.nodes
        ],
    )

    node_results = {}
    events = []

    async for event in engine.execute(workflow, initial_input=body.input):
        events.append({"type": event.event_type, "node_id": event.node_id, "data": event.data})
        if event.event_type == "node_complete" and event.node_id:
            node_results[event.node_id] = event.data

    return {
        "workflow_name": body.name,
        "node_results": node_results,
        "execution_log": events,
        "total_nodes": len(body.nodes),
        "completed_nodes": sum(1 for e in events if e["type"] == "node_complete"),
    }


@router.post(
    "/run/stream",
    summary="워크플로우 실행 (SSE 스트리밍)",
    description="""
워크플로우 실행 이벤트를 실시간 SSE 스트림으로 전달합니다.

**SSE 이벤트 타입:**
```
event: node_start
data: {"node_id": "task_a"}

event: node_complete
data: {"node_id": "task_a", "output": "태스크 A"}

event: node_failed
data: {"node_id": "task_b", "error": "오류 메시지"}

event: done
data: {"status": "completed"}
```

**실제 구현 코드:** `src/workflow/api/execution_api.py`
    """,
)
async def run_workflow_stream(body: WorkflowRunRequest):
    import uuid

    workflow = WorkflowDefinition(
        id=str(uuid.uuid4()),
        name=body.name,
        nodes=[
            NodeDefinition(
                id=n.id,
                node_type=n.node_type,
                config=n.config,
                dependencies=n.dependencies,
            )
            for n in body.nodes
        ],
    )

    async def event_stream():
        async for event in engine.execute(workflow, initial_input=body.input):
            payload = {"node_id": event.node_id}
            if event.data is not None:
                payload["data"] = str(event.data)[:500]  # 너무 긴 데이터 잘라내기

            yield f"event: {event.event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
