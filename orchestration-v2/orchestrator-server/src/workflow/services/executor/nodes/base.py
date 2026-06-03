"""Abstract base class for all workflow nodes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.workflow.services.executor.context import ExecutionContext


class BaseNode(ABC):
    """Every node type must inherit from this class.

    Nodes are stateless — all runtime state lives in ExecutionContext.
    The `config` dict is the node's `data` field from the React Flow definition.
    """

    node_type: str  # Must be set on subclass

    @abstractmethod
    async def execute(self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext") -> dict[str, Any]:
        """Run the node and return its output dict.

        Args:
            inputs: Resolved variable values available to this node.
            config: Static configuration from the workflow definition (node.data).
            ctx: Shared execution context (for logging, accessing shared state).

        Returns:
            A dict that will be stored as this node's output and made available
            to downstream nodes via ``{{nodes.<node_id>.output.<key>}}``.
        """

    def input_schema(self) -> dict:
        """JSON Schema describing the node's configuration fields.

        Used by the frontend to render the config panel form.
        Override in subclasses to return a meaningful schema.
        """
        return {}

    def output_schema(self) -> dict:
        """JSON Schema describing the node's output fields.

        Used by the frontend to show available variables for downstream nodes.
        """
        return {}
