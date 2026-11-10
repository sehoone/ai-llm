"""워크플로우 실행 이벤트 (ADR-0019 §1).

러너는 DB·SSE 문자열을 모른다 — 이 Pydantic 이벤트 객체를 async-generator로 흘린다. 도메인 서비스가
스트림을 소비하며 ① 실행/노드 행을 영속, ② `data: <json>\n\n` SSE로 직렬화한다.

필드는 web `src/api/workflows.ts`의 `SSEEvent` 유니온과 1:1이다(`type` 판별자 + 노드/실행 식별자).
`node_type`은 영속용으로 skip에도 싣되 web은 무시한다.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class NodeStartEvent(BaseModel):
    type: Literal["node_start"] = "node_start"
    node_id: str
    node_type: str
    input_data: dict[str, Any] = {}


class NodeCompleteEvent(BaseModel):
    type: Literal["node_complete"] = "node_complete"
    node_id: str
    node_type: str
    output_data: dict[str, Any] = {}


class NodeFailedEvent(BaseModel):
    type: Literal["node_failed"] = "node_failed"
    node_id: str
    node_type: str
    error: str


class NodeSkippedEvent(BaseModel):
    type: Literal["node_skipped"] = "node_skipped"
    node_id: str
    node_type: str = ""


class ExecutionCompleteEvent(BaseModel):
    type: Literal["execution_complete"] = "execution_complete"
    execution_id: str
    output_data: dict[str, Any] = {}


class ExecutionFailedEvent(BaseModel):
    type: Literal["execution_failed"] = "execution_failed"
    execution_id: str
    error: str


ExecutionEvent = (
    NodeStartEvent
    | NodeCompleteEvent
    | NodeFailedEvent
    | NodeSkippedEvent
    | ExecutionCompleteEvent
    | ExecutionFailedEvent
)
