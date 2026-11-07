"""승인 게이트가 있는 챗 그래프 (ADR-0008 §2).

흐름: agent → (tool_calls?) → approval_gate(interrupt) → tools → agent → … → END

- `agent`: 주입된 모델이 다음 발화/도구호출을 결정. (engine/llm 이식 전까지 주입 seam)
- `approval_gate`: 각 tool call을 정책으로 판정. CONFIRM이 있으면 `interrupt()`로 중단,
  사용자 결정(resume 값)으로 승인/거부/인자수정을 반영.
- `tools`: 승인된 호출만 실행하고 결과를 ToolMessage로 되돌린다.

engine 규칙(ADR-0005): FastAPI·domains 비의존. 역할·오버라이드는 config로 주입받는다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, Protocol, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from src.engine.agent.policy import ApprovalPolicy, Decision, PolicyContext, ToolCall
from src.engine.agent.registry import ToolRegistry


class ChatModel(Protocol):
    """그래프가 요구하는 최소 모델 인터페이스.

    `config`는 LangGraph가 노드에 준 RunnableConfig — `stream_mode="messages"` 토큰 콜백이
    LLM 호출까지 전파되도록 모델이 내부 Runnable에 포워딩한다(ADR-0011 §2).
    """

    def invoke(self, messages: list[BaseMessage], config: RunnableConfig | None = None) -> AIMessage: ...


class ChatState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    # approval_gate → tools 사이 한 슈퍼스텝 내 전달되는 결정 맵. tool_call_id -> {approved, args}
    decisions: dict[str, Any]


def _policy_ctx(config: RunnableConfig) -> PolicyContext:
    """config.configurable에서 주입된 역할·오버라이드로 PolicyContext 복원."""
    cfg = (config or {}).get("configurable", {})
    return PolicyContext(
        role=cfg.get("role", "USER"),
        auto_approve_tools=frozenset(cfg.get("auto_approve_tools", ())),
    )


def _tool_calls(msg: BaseMessage) -> list[dict[str, Any]]:
    return list(getattr(msg, "tool_calls", None) or [])


def build_chat_graph(
    *,
    model: "ChatModel | Callable[[RunnableConfig], ChatModel]",
    registry: ToolRegistry,
    policy: ApprovalPolicy,
    checkpointer: BaseCheckpointSaver,
):
    """HITL 승인 게이트가 포함된 컴파일된 챗 그래프를 반환.

    `model`은 고정 `ChatModel`이거나 `config`를 받아 모델을 고르는 **리졸버 함수**일 수 있다
    (per-request 모델 선택 — ADR-0011 §4). 도메인이 `config.configurable`에 선택을 주입하고
    리졸버가 해석한다(ADR-0005 — 도메인이 값 주입, engine은 DB 미조회).
    """

    def agent(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
        # 리졸버면 config로 모델 선택, 아니면 고정 모델 사용.
        m: ChatModel = model(config) if callable(model) else model
        # config 전달 → 토큰 스트리밍 콜백이 LLM 호출까지 전파 (ADR-0011 §2).
        ai = m.invoke(state["messages"], config)
        return {"messages": [ai]}

    def route(state: ChatState) -> str:
        return "gate" if _tool_calls(state["messages"][-1]) else END

    def approval_gate(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
        ai = state["messages"][-1]
        ctx = _policy_ctx(config)
        decisions: dict[str, Any] = {}
        confirm_requests: list[dict[str, Any]] = []

        for tc in _tool_calls(ai):
            result = policy.evaluate(ToolCall(id=tc["id"], name=tc["name"], args=tc["args"]), ctx)
            if result.decision is Decision.ALLOW:
                decisions[tc["id"]] = {"approved": True, "args": tc["args"]}
            elif result.decision is Decision.BLOCK:
                decisions[tc["id"]] = {"approved": False, "reason": result.reason}
            else:  # CONFIRM → 사용자에게 묻는다
                confirm_requests.append(
                    {
                        "tool_call_id": tc["id"],
                        "name": tc["name"],
                        "args": tc["args"],
                        "tier": str(result.tier),
                        "allow_edit": result.allow_edit,
                        "reason": result.reason,
                    }
                )

        if confirm_requests:
            # 그래프 일시중지 → 체크포인트 저장. resume 값으로 여기 재개.
            # human: {tool_call_id: {"approved": bool, "args"?: {...}}}
            human = interrupt({"type": "approval_required", "requests": confirm_requests})
            for req in confirm_requests:
                cid = req["tool_call_id"]
                d = (human or {}).get(cid)
                if not d:  # 결정 누락 = 거부 (fail-safe, ADR-0008 §5)
                    decisions[cid] = {"approved": False, "reason": "미결정(기본 거부)"}
                    continue
                approved = bool(d.get("approved"))
                # 인자 수정은 allow_edit일 때만 반영
                args = d.get("args") if (req["allow_edit"] and d.get("args")) else req["args"]
                decisions[cid] = {"approved": approved, "args": args, "reason": d.get("reason")}

        return {"decisions": decisions}

    def tools(state: ChatState) -> dict[str, Any]:
        ai = state["messages"][-1]
        decisions = state.get("decisions", {})
        out: list[BaseMessage] = []
        for tc in _tool_calls(ai):
            d = decisions.get(tc["id"], {"approved": False, "reason": "미결정"})
            if not d.get("approved"):
                out.append(
                    ToolMessage(
                        content=f"[거부됨] '{tc['name']}' 실행이 승인되지 않았습니다. "
                        f"({d.get('reason') or 'rejected'})",
                        tool_call_id=tc["id"],
                        name=tc["name"],
                    )
                )
                continue
            spec = registry.get(tc["name"])
            args = d.get("args") or tc["args"]
            try:
                content = str(spec.handler(**args)) if spec else f"[오류] 미등록 도구 {tc['name']}"
            except Exception as e:  # noqa: BLE001 — 도구 오류를 모델에 되돌려 복구 기회를 준다
                content = f"[오류] {tc['name']} 실행 실패: {e}"
            out.append(ToolMessage(content=content, tool_call_id=tc["id"], name=tc["name"]))
        return {"messages": out, "decisions": {}}

    graph = StateGraph(ChatState)
    graph.add_node("agent", agent)
    graph.add_node("gate", approval_gate)
    graph.add_node("tools", tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route, {"gate": "gate", END: END})
    graph.add_edge("gate", "tools")
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)
