"""ExecutionContext and template variable resolver.

Variable syntax:
    {{input.<key>}}               — workflow input_data
    {{nodes.<node_id>.output.<key>}}  — specific node output field
    {{nodes.<node_id>.output}}    — entire node output dict (JSON-serialised)

Resolving is recursive for dict/list values so nested templates work.
"""

from __future__ import annotations

import json
import re
from typing import Any

_TEMPLATE_RE = re.compile(r"\{\{\s*([\w.\[\]\-]+)\s*\}\}")


class ExecutionContext:
    """Shared runtime state for a single workflow execution."""

    def __init__(self, execution_id: str, input_data: dict[str, Any], user_id: int | None = None) -> None:
        self.execution_id = execution_id
        self.input_data: dict[str, Any] = input_data
        self.user_id: int | None = user_id
        # node_id → output dict
        self._node_outputs: dict[str, dict[str, Any]] = {}
        # node_id → "true" | "false" (for condition nodes)
        self._condition_results: dict[str, bool] = {}

    # ── node output management ────────────────────────────────────────────────

    def set_node_output(self, node_id: str, output: dict[str, Any]) -> None:
        self._node_outputs[node_id] = output

    def get_node_output(self, node_id: str) -> dict[str, Any]:
        return self._node_outputs.get(node_id, {})

    def set_condition_result(self, node_id: str, result: bool) -> None:
        self._condition_results[node_id] = result

    def get_condition_result(self, node_id: str) -> bool | None:
        return self._condition_results.get(node_id)

    # ── template resolution ───────────────────────────────────────────────────

    def resolve(self, value: Any) -> Any:
        """Recursively resolve template expressions in `value`."""
        if isinstance(value, str):
            return self._resolve_string(value)
        if isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        return value

    def _resolve_string(self, template: str) -> Any:
        """Resolve all {{...}} placeholders in a string.

        If the *entire* string is a single placeholder and its resolved value
        is not a string, return the raw value (preserves types like bool/dict).
        """
        matches = _TEMPLATE_RE.findall(template)
        if not matches:
            return template

        # Single placeholder that fills the whole string → return raw value
        if len(matches) == 1 and template.strip() == f"{{{{{matches[0]}}}}}":
            return self._lookup(matches[0])

        # Multiple placeholders or embedded → stringify each
        def replacer(m: re.Match) -> str:
            val = self._lookup(m.group(1))
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val) if val is not None else ""

        return _TEMPLATE_RE.sub(replacer, template)

    def _lookup(self, path: str) -> Any:
        """Resolve a dot-separated path like 'nodes.llm-1.output.text'."""
        parts = path.split(".")

        if parts[0] == "input":
            # {{input.key}}
            if len(parts) < 2:
                return self.input_data
            return self._deep_get(self.input_data, parts[1:])

        if parts[0] == "nodes" and len(parts) >= 3:
            node_id = parts[1]
            # parts[2] should be "output"
            node_output = self._node_outputs.get(node_id, {})
            if len(parts) == 3:
                # {{nodes.node_id.output}} — return whole output dict
                return node_output
            return self._deep_get(node_output, parts[3:])

        return None

    @staticmethod
    def _deep_get(data: Any, keys: list[str]) -> Any:
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return None
        return data

    def resolve_node_inputs(self, node_config: dict[str, Any]) -> dict[str, Any]:
        """Resolve all template expressions in a node's config dict.

        Returns a new dict with resolved values — used as the `inputs` arg
        passed to node.execute().
        """
        return self.resolve(node_config)
