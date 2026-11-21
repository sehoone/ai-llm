"""되묻기(ask_user) 그래프 흐름 테스트 (ADR-0025 / ADR-0026). 실 LLM 없이 결정적으로 검증한다.

그래프 노드가 async(ADR-0026)라 `astream`으로 구동한다. pytest-asyncio 의존 없이 `asyncio.run`으로
async 헬퍼를 감싼다. 스텁 모델이 ask_user를 1회 호출 → interrupt 중단 → 사용자 답변으로 재개 →
답변이 ToolMessage로 주입되고 최종 답변이 생성되는지 확인한다.
"""

import asyncio
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from src.engine.agent.policy import ApprovalPolicy
from src.engine.agent.tools import default_registry
from src.engine.graph.chat_graph import build_chat_graph


class AskThenAnswerModel:
    """ask_user를 한 번 호출하고, 답변(ToolMessage)을 받으면 최종 답변을 낸다 (async ChatModel)."""

    async def ainvoke(self, messages: list[BaseMessage], config: Any = None) -> AIMessage:
        for m in messages:
            if isinstance(m, ToolMessage):
                return AIMessage(content=f"{m.content} 기준으로 처리했습니다.")
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "ask_user",
                    "args": {
                        "question": "어느 기간의 데이터를 말씀하시나요?",
                        "options": [{"value": "7d", "label": "최근 7일"}],
                    },
                    "id": "call_ask_1",
                    "type": "tool_call",
                }
            ],
        )


def _graph():
    registry = default_registry()
    return build_chat_graph(
        model=AskThenAnswerModel(),
        registry=registry,
        policy=ApprovalPolicy(registry),
        checkpointer=InMemorySaver(),
    )


async def _collect(graph, graph_input, config) -> tuple[Any, list[BaseMessage]]:
    """astream을 끝까지 돌며 interrupt payload와 누적 메시지를 반환."""
    interrupted = None
    msgs: list[BaseMessage] = []
    async for _mode, chunk in graph.astream(graph_input, config=config, stream_mode=["updates"]):
        if "__interrupt__" in chunk:
            interrupted = chunk["__interrupt__"][0].value
            continue
        for update in chunk.values():
            if isinstance(update, dict):
                msgs.extend(update.get("messages", []) or [])
    return interrupted, msgs


def test_ask_user_interrupts_with_clarification_payload() -> None:
    graph = _graph()
    config = {"configurable": {"thread_id": "t1"}}
    interrupted, _msgs = asyncio.run(
        _collect(graph, {"messages": [HumanMessage(content="보고서 만들어줘")]}, config)
    )
    assert interrupted is not None
    assert interrupted["type"] == "clarification_required"
    req = interrupted["requests"][0]
    assert req["tool_call_id"] == "call_ask_1"
    assert req["question"]
    assert req["options"] == [{"value": "7d", "label": "최근 7일"}]
    assert req["allow_free_text"] is True


def test_clarify_resume_injects_answer_and_completes() -> None:
    graph = _graph()
    config = {"configurable": {"thread_id": "t2"}}

    async def _run() -> list[BaseMessage]:
        # 1) 중단까지 구동
        await _collect(graph, {"messages": [HumanMessage(content="보고서 만들어줘")]}, config)
        # 2) 사용자 보기 선택(value=7d)으로 재개
        _itr, msgs = await _collect(graph, Command(resume={"call_ask_1": {"value": "7d"}}), config)
        return msgs

    msgs = asyncio.run(_run())
    # 되묻기 답변이 ToolMessage로 주입됨
    tool_msgs = [m for m in msgs if isinstance(m, ToolMessage)]
    assert any(t.content == "7d" for t in tool_msgs)
    # 최종 답변이 그 답변을 반영
    ai_finals = [m for m in msgs if isinstance(m, AIMessage) and m.content]
    assert any("7d" in m.content for m in ai_finals)
