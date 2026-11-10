"""모든 워크플로우 노드의 추상 베이스 (V2 계승)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext


class BaseNode(ABC):
    """모든 노드 타입은 이 클래스를 상속한다.

    노드는 무상태(stateless)다 — 런타임 상태는 전부 ExecutionContext에 있다. `config` dict는
    React Flow 정의의 node.data 필드다.
    """

    node_type: str  # 서브클래스에서 설정

    @abstractmethod
    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
        """노드를 실행하고 출력 dict를 반환.

        Args:
            inputs: 템플릿 해석이 끝난 이 노드의 입력 값.
            config: 워크플로우 정의의 정적 설정(node.data) — 원본(미해석).
            ctx: 공유 실행 컨텍스트.

        Returns:
            이 노드의 출력으로 저장되고 `{{nodes.<id>.output.<key>}}`로 하위 노드에 노출될 dict.
        """

    def input_schema(self) -> dict:
        """노드 설정 필드 JSON Schema — 프론트 config 패널 렌더용. 서브클래스에서 override."""
        return {}

    def output_schema(self) -> dict:
        """노드 출력 필드 JSON Schema — 프론트 변수 목록 표시용. 서브클래스에서 override."""
        return {}
