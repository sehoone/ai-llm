"""샘플 02: 딥씽킹 에이전트 — 그래프 조립

실제 구현: src/common/langgraph/graph.py

핵심 개념:
- 조건부 엣지(add_conditional_edges): 라우팅 함수의 반환값에 따라 다음 노드 결정
- Command(goto=): 노드가 직접 다음 노드를 지정 (동적 라우팅)
- set_finish_point: verify 노드가 END를 결정하므로 종료 가능 노드로 등록

그래프 구조:
    START ──(route_start)──► think ──► chat ──► verify ──► END
                │                      ▲         │
                └──────────────────────┘         │
                         (복잡하지 않은 질문)      │ (approved=False)
                                                 ▼
                                    chat ──► verify ──► END
"""

import asyncio
from typing import Optional

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from .nodes import chat_node, route_start, think_node, verify_node
from .state import DeepThinkingState


def build_graph():
    """딥씽킹 그래프를 빌드하고 컴파일한다.

    체크포인터를 추가하려면:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        checkpointer = AsyncPostgresSaver(pool)
        graph = builder.compile(checkpointer=checkpointer)

    여기서는 단순화를 위해 메모리 체크포인터 없이 빌드.
    """
    builder = StateGraph(DeepThinkingState)

    # 노드 등록
    # ends=[]: 이 노드에서 goto할 수 있는 노드 목록 (타입 안전성)
    builder.add_node("think", think_node, ends=["chat"])
    builder.add_node("chat", chat_node, ends=["verify"])
    builder.add_node("verify", verify_node, ends=["chat", END])

    # 시작점: route_start 함수가 "think" 또는 "chat" 반환
    builder.add_conditional_edges(START, route_start)

    # verify가 END를 직접 결정하므로 종료 가능 노드로 등록
    builder.set_finish_point("verify")

    return builder.compile()


async def run_deep_thinking_example():
    """딥씽킹 예시 실행."""
    graph = build_graph()

    print("=== 일반 질문 (chat만 실행) ===")
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="Python에서 리스트와 튜플의 차이는?")],
            "is_deep_thinking": False,
        }
    )
    # messages에서 assistant 응답만 필터링
    for msg in result["messages"]:
        if hasattr(msg, "type") and msg.type == "ai":
            print(f"응답: {msg.content[:200]}...\n")

    print("=== 딥씽킹 질문 (think → chat → verify 실행) ===")
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="마이크로서비스 아키텍처와 모놀리식의 장단점을 비교 분석해주세요.")],
            "is_deep_thinking": True,
        }
    )

    # 각 단계별 메시지 출력
    for msg in result["messages"]:
        if hasattr(msg, "type") and msg.type == "ai" and hasattr(msg, "content"):
            content = str(msg.content)
            if "[Deep Thinking - Analysis]" in content:
                print(f"[THINK 노드]\n{content[:300]}...\n")
            elif "[Deep Thinking - Verification]" in content:
                print(f"[VERIFY 노드]\n{content[:300]}...\n")
            elif "[Deep Thinking - Answer]" in content:
                print(f"[CHAT 노드 최종 답변]\n{content[:300]}...\n")


if __name__ == "__main__":
    asyncio.run(run_deep_thinking_example())
