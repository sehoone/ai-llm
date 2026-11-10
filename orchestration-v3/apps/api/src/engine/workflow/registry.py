"""노드 타입 레지스트리 (V2 계승).

node_type 문자열 → 노드 클래스. 프론트 팔레트는 `list_node_types()`로 각 노드의 input/output 스키마를
받아 config 패널을 렌더한다. 새 노드 추가: nodes/에 BaseNode 서브클래스 작성 → 아래에 import·등록.
"""

from __future__ import annotations

from src.engine.workflow.nodes.base import BaseNode
from src.engine.workflow.nodes.code import CodeNode
from src.engine.workflow.nodes.condition import ConditionNode
from src.engine.workflow.nodes.end import EndNode
from src.engine.workflow.nodes.http import HTTPNode
from src.engine.workflow.nodes.llm import LLMNode
from src.engine.workflow.nodes.loop import LoopNode
from src.engine.workflow.nodes.rag import RAGNode
from src.engine.workflow.nodes.start import StartNode
from src.engine.workflow.nodes.tool import ToolNode

_REGISTRY: dict[str, type[BaseNode]] = {}


def _register(*node_classes: type[BaseNode]) -> None:
    for cls in node_classes:
        _REGISTRY[cls.node_type] = cls


_register(StartNode, EndNode, LLMNode, ConditionNode, RAGNode, HTTPNode, CodeNode, ToolNode, LoopNode)


def get_node(node_type: str) -> BaseNode:
    """node_type에 해당하는 노드 인스턴스 반환. 미등록이면 ValueError."""
    cls = _REGISTRY.get(node_type)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown node type '{node_type}'. Available: {available}")
    return cls()


def list_node_types() -> list[dict]:
    """등록된 모든 노드의 메타(프론트 팔레트용)."""
    result = []
    for node_type, cls in sorted(_REGISTRY.items()):
        instance = cls()
        result.append(
            {
                "type": node_type,
                "input_schema": instance.input_schema(),
                "output_schema": instance.output_schema(),
            }
        )
    return result
