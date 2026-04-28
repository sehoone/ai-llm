"""샘플 02: 딥씽킹 에이전트 상태 정의

실제 구현: src/common/schemas/graph.py
"""

from typing import Annotated, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class DeepThinkingState(BaseModel):
    """딥씽킹 에이전트의 공유 상태.

    각 필드의 역할:
    - messages: 전체 대화 히스토리 (think/verify 분석 메시지 포함)
    - is_deep_thinking: think → verify 루프 활성화 여부
    - thinking_context: think 노드가 chat 노드에 전달하는 전략 계획
    - verify_feedback: verify 노드가 chat 노드에 전달하는 개선 지시사항
    - verify_iterations: verify → chat 재시도 횟수 (무한루프 방지)
    """

    messages: Annotated[list, add_messages] = Field(default_factory=list)
    is_deep_thinking: bool = Field(default=False)
    thinking_context: Optional[str] = Field(default=None)
    verify_feedback: Optional[str] = Field(default=None)
    verify_iterations: int = Field(default=0)
