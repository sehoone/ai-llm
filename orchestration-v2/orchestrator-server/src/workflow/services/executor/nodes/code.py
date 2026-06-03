"""Code node — execute a Python snippet in a restricted environment.

Config schema:
    {
        "code": "result = {'doubled': input_data['number'] * 2}"
    }

Available names inside the snippet:
    input_data  — the workflow input dict ({{input.*}})
    nodes       — dict of node_id → output dict for all completed nodes
    json        — the json standard module
    re          — the re standard module
    math        — the math standard module

The snippet MUST assign to the name ``result`` (a dict).
If ``result`` is not a dict after execution it is wrapped: {"value": result}.

Forbidden: __import__, open, exec, eval, file system ops, network, globals().

Output:
    whatever the snippet sets ``result`` to (must be JSON-serialisable)
"""

from __future__ import annotations

import json
import math
import re as _re
import traceback
from typing import TYPE_CHECKING, Any

from src.common.logging import logger
from src.workflow.services.executor.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.workflow.services.executor.context import ExecutionContext

# Allowed built-ins — everything not in this list raises NameError
_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "chr": chr,
    "dict": dict, "divmod": divmod, "enumerate": enumerate, "filter": filter,
    "float": float, "format": format, "frozenset": frozenset, "getattr": getattr,
    "hasattr": hasattr, "hash": hash, "int": int, "isinstance": isinstance,
    "issubclass": issubclass, "iter": iter, "len": len, "list": list,
    "map": map, "max": max, "min": min, "next": next, "ord": ord,
    "pow": pow, "print": print, "range": range, "repr": repr,
    "reversed": reversed, "round": round, "set": set, "slice": slice,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple, "type": type,
    "zip": zip,
    "True": True, "False": False, "None": None,
}


class CodeNode(BaseNode):
    node_type = "code"

    async def execute(self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext") -> dict[str, Any]:
        code: str = config.get("code", "").strip()
        if not code:
            raise ValueError("Code node requires non-empty 'code'.")

        # Build execution namespace
        namespace: dict[str, Any] = {
            "__builtins__": _SAFE_BUILTINS,
            "input_data": ctx.input_data,
            "nodes": ctx._node_outputs,  # read-only dict view
            "json": json,
            "re": _re,
            "math": math,
        }

        try:
            # compile → exec (restricted globals)
            compiled = compile(code, "<workflow_code_node>", "exec")
            exec(compiled, namespace)  # noqa: S102
        except Exception as exc:
            tb = traceback.format_exc()
            raise RuntimeError(f"Code execution error:\n{tb}") from exc

        result = namespace.get("result")
        if result is None:
            raise ValueError("Code node must assign a value to 'result'.")

        # Ensure result is serialisable
        if not isinstance(result, dict):
            result = {"value": result}

        logger.info("code_node_executed", code_length=len(code))
        return result

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": (
                        "Python snippet. Assign output to `result` (dict). "
                        "Available: input_data, nodes, json, re, math."
                    ),
                }
            },
            "required": ["code"],
        }

    def output_schema(self) -> dict:
        return {
            "type": "object",
            "description": "The dict assigned to `result` inside the code snippet.",
        }
