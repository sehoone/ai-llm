"""Node type registry.

Import all node classes here and register them so the engine can look up
a node class by its `node_type` string at runtime.

To add a new node type:
    1. Create a new file in nodes/
    2. Subclass BaseNode and set `node_type`
    3. Import and register it below
"""

from src.workflow.services.executor.nodes.base import BaseNode
from src.workflow.services.executor.nodes.start import StartNode
from src.workflow.services.executor.nodes.end import EndNode
from src.workflow.services.executor.nodes.llm import LLMNode
from src.workflow.services.executor.nodes.condition import ConditionNode
from src.workflow.services.executor.nodes.rag import RAGNode
from src.workflow.services.executor.nodes.http import HTTPNode
from src.workflow.services.executor.nodes.code import CodeNode
from src.workflow.services.executor.nodes.tool import ToolNode
from src.workflow.services.executor.nodes.loop import LoopNode

_REGISTRY: dict[str, type[BaseNode]] = {}


def _register(*node_classes: type[BaseNode]) -> None:
    for cls in node_classes:
        _REGISTRY[cls.node_type] = cls


_register(StartNode, EndNode, LLMNode, ConditionNode, RAGNode, HTTPNode, CodeNode, ToolNode, LoopNode)


def get_node(node_type: str) -> BaseNode:
    """Return an instance of the node class for `node_type`.

    Raises:
        ValueError: If node_type is not registered.
    """
    cls = _REGISTRY.get(node_type)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown node type '{node_type}'. Available: {available}")
    return cls()


def list_node_types() -> list[dict]:
    """Return metadata for all registered node types (used by the frontend palette)."""
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
