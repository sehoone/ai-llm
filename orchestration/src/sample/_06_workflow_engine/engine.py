"""샘플 06: 워크플로우 DAG 실행 엔진

실제 구현: src/workflow/services/executor/engine.py

핵심 개념:
- DAG (Directed Acyclic Graph): 순환이 없는 방향 그래프 — 순서가 있는 작업 의존성 표현
- 병렬 실행: 모든 의존성이 완료된 노드를 동시에 실행 (asyncio.gather)
- SSE 이벤트 큐: 실행 중 상태를 실시간으로 클라이언트에 전달
- 노드 타입 레지스트리: 새 노드 타입을 코드 수정 없이 추가 가능

실행 순서 예시:
    start → [fetch_data, load_config] → process → [save_result, notify] → end

    fetch_data와 load_config는 start 완료 후 동시 실행 (asyncio.gather)
    process는 둘 다 완료된 후 실행
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional


# ── 워크플로우 정의 ────────────────────────────────────────────────────────────

@dataclass
class NodeDefinition:
    """워크플로우 노드 하나의 정의.

    node_type이 어떤 작업을 수행할지, config가 파라미터를 제공.
    """
    id: str
    node_type: str          # "llm" | "http" | "code" | "condition" 등
    config: Dict[str, Any]  # 노드 타입별 설정
    dependencies: List[str] = field(default_factory=list)  # 이 노드 실행 전 완료되어야 할 노드 ID 목록


@dataclass
class WorkflowDefinition:
    """실행할 워크플로우 전체 정의."""
    id: str
    name: str
    nodes: List[NodeDefinition]


# ── 실행 상태 ──────────────────────────────────────────────────────────────────

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # 조건부 분기에서 실행 안 된 노드


@dataclass
class NodeResult:
    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None


# ── SSE 이벤트 ────────────────────────────────────────────────────────────────

@dataclass
class ExecutionEvent:
    """실행 이벤트 — SSE로 클라이언트에 전달."""
    event_type: str  # "node_start" | "node_complete" | "node_failed" | "done"
    node_id: Optional[str] = None
    data: Any = None


# ── 노드 타입 레지스트리 ───────────────────────────────────────────────────────

NodeHandler = Callable[[Dict[str, Any], Dict[str, Any]], Any]

_NODE_REGISTRY: Dict[str, NodeHandler] = {}


def register_node(node_type: str):
    """노드 타입 등록 데코레이터.

    실제 코드 (src/workflow/services/executor/registry.py):
        @register_node("llm")
        async def llm_node(config, context): ...

        @register_node("http")
        async def http_node(config, context): ...
    """
    def decorator(fn: NodeHandler) -> NodeHandler:
        _NODE_REGISTRY[node_type] = fn
        return fn
    return decorator


# ── 기본 노드 구현 ─────────────────────────────────────────────────────────────

@register_node("echo")
async def echo_node(config: Dict, context: Dict) -> str:
    """입력 메시지를 그대로 반환 — 테스트/디버그용."""
    await asyncio.sleep(0.1)  # 실제 작업 시뮬레이션
    message = config.get("message", "")
    return f"[echo] {message}"


@register_node("http")
async def http_node(config: Dict, context: Dict) -> Dict:
    """HTTP 요청 실행 노드.

    실제 코드 (src/workflow/services/executor/nodes/http.py):
        async with aiohttp.ClientSession() as session:
            response = await session.request(method, url, json=body, headers=headers)
            return await response.json()
    """
    import aiohttp
    url = config["url"]
    method = config.get("method", "GET")
    body = config.get("body")

    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, json=body) as response:
            return {"status": response.status, "body": await response.json()}


@register_node("code")
async def code_node(config: Dict, context: Dict) -> Any:
    """Python 코드 실행 노드.

    실제 코드에서는 sandbox 환경에서 실행하여 보안 위험 최소화.
    context에 이전 노드 출력이 담겨 있어 참조 가능.
    """
    code = config.get("code", "result = None")

    # 이전 노드 출력을 로컬 변수로 주입
    local_vars = {"context": context, "result": None}
    exec(code, {}, local_vars)  # noqa: S102 — 실제로는 sandbox 사용
    return local_vars.get("result")


@register_node("llm")
async def llm_node(config: Dict, context: Dict) -> str:
    """LLM 호출 노드.

    실제 코드 (src/workflow/services/executor/nodes/llm.py):
        agent = LangGraphAgent()
        response = await agent.get_response(messages, session_id, ...)
        return response[-1]["content"]
    """
    await asyncio.sleep(0.5)  # LLM 호출 시뮬레이션
    prompt = config.get("prompt", "")
    return f"[LLM 응답] {prompt}에 대한 답변입니다."


@register_node("condition")
async def condition_node(config: Dict, context: Dict) -> str:
    """조건 분기 노드 — 다음에 실행할 분기 ID를 반환.

    실제 코드에서는 반환된 분기 ID를 기반으로
    도달 불가능한 노드들을 SKIPPED 처리.
    """
    condition = config.get("condition", "true")
    true_branch = config.get("true_branch", "")
    false_branch = config.get("false_branch", "")

    # 실제: context 값을 참조하여 조건 평가
    result = eval(condition, {"context": context})  # noqa: S307
    return true_branch if result else false_branch


# ── DAG 실행 엔진 ──────────────────────────────────────────────────────────────

class WorkflowEngine:
    """DAG 기반 워크플로우 실행 엔진.

    핵심 알고리즘:
    1. 완료된 의존성 노드가 모두 있는 노드를 "준비됨(ready)" 상태로 판단
    2. ready 노드들을 asyncio.gather로 병렬 실행
    3. 실행 완료 시 결과를 context에 저장
    4. 다시 ready 노드 찾기 반복 → 모든 노드 완료 시 종료

    실제 코드 (src/workflow/services/executor/engine.py)에서는:
    - DB에 각 NodeExecution 상태 저장
    - SSE 이벤트 큐에 이벤트 추가
    - 조건부 분기에서 unreachable 노드 SKIPPED 처리
    """

    async def execute(
        self,
        workflow: WorkflowDefinition,
        initial_input: Dict[str, Any] = None,
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """워크플로우를 실행하고 SSE 이벤트를 yield한다."""
        context: Dict[str, Any] = {"input": initial_input or {}}
        results: Dict[str, NodeResult] = {}
        node_map = {n.id: n for n in workflow.nodes}

        # 이벤트 큐 (SSE 이벤트를 순서대로 전달)
        event_queue: asyncio.Queue[ExecutionEvent] = asyncio.Queue()

        async def run_node(node: NodeDefinition):
            """단일 노드 실행 + 이벤트 발행."""
            await event_queue.put(ExecutionEvent("node_start", node.id))

            handler = _NODE_REGISTRY.get(node.node_type)
            if not handler:
                result = NodeResult(node.id, NodeStatus.FAILED, error=f"알 수 없는 노드 타입: {node.node_type}")
                await event_queue.put(ExecutionEvent("node_failed", node.id, result.error))
            else:
                try:
                    output = await handler(node.config, context)
                    result = NodeResult(node.id, NodeStatus.COMPLETED, output=output)
                    context[node.id] = output  # 이후 노드에서 참조 가능
                    await event_queue.put(ExecutionEvent("node_complete", node.id, output))
                except Exception as e:
                    result = NodeResult(node.id, NodeStatus.FAILED, error=str(e))
                    await event_queue.put(ExecutionEvent("node_failed", node.id, str(e)))

            results[node.id] = result

        async def execution_loop():
            """의존성 기반 병렬 실행 루프."""
            while True:
                # 실행 가능한(ready) 노드 찾기: 미완료이면서 모든 의존성이 완료된 노드
                ready = [
                    node for node in workflow.nodes
                    if node.id not in results
                    and all(
                        results.get(dep_id, NodeResult("", NodeStatus.PENDING)).status == NodeStatus.COMPLETED
                        for dep_id in node.dependencies
                    )
                ]

                if not ready:
                    # 더 실행할 노드가 없으면 종료
                    break

                # 준비된 노드들을 병렬 실행
                print(f"  병렬 실행: {[n.id for n in ready]}")
                await asyncio.gather(*[run_node(node) for node in ready])

            await event_queue.put(ExecutionEvent("done"))

        # 실행 루프를 백그라운드 태스크로 시작
        task = asyncio.create_task(execution_loop())

        # 이벤트 큐에서 이벤트를 꺼내 yield
        while True:
            event = await event_queue.get()
            yield event
            if event.event_type == "done":
                break

        await task


# ── 실행 예시 ──────────────────────────────────────────────────────────────────

async def main():
    """워크플로우 실행 예시."""
    workflow = WorkflowDefinition(
        id="wf-001",
        name="샘플 워크플로우",
        nodes=[
            NodeDefinition("start", "echo", {"message": "시작"}, dependencies=[]),
            NodeDefinition("fetch_a", "echo", {"message": "데이터 A 로드"}, dependencies=["start"]),
            NodeDefinition("fetch_b", "echo", {"message": "데이터 B 로드"}, dependencies=["start"]),
            NodeDefinition("process", "code", {"code": "result = f'처리 완료: {context}'"},
                          dependencies=["fetch_a", "fetch_b"]),
            NodeDefinition("llm_analyze", "llm", {"prompt": "결과 분석"},
                          dependencies=["process"]),
            NodeDefinition("end", "echo", {"message": "완료"}, dependencies=["llm_analyze"]),
        ]
    )

    print(f"워크플로우 '{workflow.name}' 실행 시작\n")

    engine = WorkflowEngine()
    async for event in engine.execute(workflow, initial_input={"user_query": "테스트"}):
        if event.event_type == "node_start":
            print(f"▶ 시작: {event.node_id}")
        elif event.event_type == "node_complete":
            print(f"✓ 완료: {event.node_id} → {str(event.data)[:50]}")
        elif event.event_type == "node_failed":
            print(f"✗ 실패: {event.node_id} → {event.data}")
        elif event.event_type == "done":
            print("\n전체 워크플로우 완료!")


if __name__ == "__main__":
    asyncio.run(main())
