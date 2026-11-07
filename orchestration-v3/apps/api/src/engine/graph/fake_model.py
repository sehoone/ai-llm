"""데모용 가짜 tool-calling 모델 (ADR-0008 후속 — engine/llm 이식 시 교체).

실제 LLM 없이 승인(HITL) 흐름을 end-to-end로 구동·검증하기 위한 결정적 스텁이다.
동작: 아직 도구 결과가 없으면 `send_email`(CONFIRM) 호출을 1건 제안하고, 도구 결과가
생기면 최종 답변을 낸다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage


class FakeToolCallingModel:
    """ChatModel Protocol 구현(데모). 운영에서는 engine/llm 실모델로 대체한다."""

    def invoke(self, messages: list[BaseMessage], config: Any = None) -> AIMessage:
        if any(isinstance(m, ToolMessage) for m in messages):
            last_tool = next(m for m in reversed(messages) if isinstance(m, ToolMessage))
            return AIMessage(content=f"처리했습니다. 결과: {last_tool.content}")

        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "send_email",
                    "args": {
                        "to": "user@example.com",
                        "subject": "확인 요청",
                        "body": "승인 흐름 데모 메일입니다.",
                    },
                    "id": "call_demo_1",
                    "type": "tool_call",
                }
            ],
        )
