"""Code 노드 — 제한 환경에서 Python 스니펫 실행 (V2 계승).

config: {"code": "result = {'doubled': input_data['number'] * 2}"}
스니펫 네임스페이스: input_data·nodes·json·re·math. `result`(dict)에 대입해야 한다.

⚠️ 보안(ADR-0019): 제한 builtins 기반 exec로 샌드박스가 완전하지 않다. 신뢰 사용자/관리자 경계 전용.
"""

from __future__ import annotations

import json
import logging
import math
import re as _re
import traceback
from typing import TYPE_CHECKING, Any

from src.engine.workflow.nodes.base import BaseNode

if TYPE_CHECKING:
    from src.engine.workflow.context import ExecutionContext

logger = logging.getLogger(__name__)

# 허용 builtins — 목록 밖은 NameError
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

    async def execute(
        self, inputs: dict[str, Any], config: dict[str, Any], ctx: "ExecutionContext"
    ) -> dict[str, Any]:
        code: str = config.get("code", "").strip()
        if not code:
            raise ValueError("Code node requires non-empty 'code'.")

        namespace: dict[str, Any] = {
            "__builtins__": _SAFE_BUILTINS,
            "input_data": ctx.input_data,
            "nodes": ctx._node_outputs,
            "json": json,
            "re": _re,
            "math": math,
        }

        try:
            compiled = compile(code, "<workflow_code_node>", "exec")
            exec(compiled, namespace)  # noqa: S102
        except Exception as exc:
            tb = traceback.format_exc()
            raise RuntimeError(f"Code execution error:\n{tb}") from exc

        result = namespace.get("result")
        if result is None:
            raise ValueError("Code node must assign a value to 'result'.")
        if not isinstance(result, dict):
            result = {"value": result}

        logger.info("code_node_executed code_length=%d", len(code))
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
        return {"type": "object", "description": "The dict assigned to `result`."}
