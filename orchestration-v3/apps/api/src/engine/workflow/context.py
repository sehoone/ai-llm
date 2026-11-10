"""ExecutionContext + 템플릿 변수 리졸버 (ADR-0019, V2 context.py 계승).

변수 문법 (n8n expression과 유사):
    {{input.<key>}}                   — 워크플로우 input_data
    {{nodes.<node_id>.output.<key>}}  — 특정 노드 출력 필드
    {{nodes.<node_id>.output}}        — 노드 출력 dict 전체(JSON 직렬화)

dict/list 값은 재귀 해석한다. 문자열 전체가 단일 placeholder면 원시 타입(bool/dict 등)을 보존한다.

engine 순수성(ADR-0005): 외부 의존은 **주입**받는다 — `rag_search` 포트, `llm_config` 값.
ctx는 DB·FastAPI·domains를 import하지 않는다.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.engine.llm.config import LlmConfig
    from src.engine.workflow.ports import RagSearch

    # resource_id(없으면 None) → LlmConfig(기본 chat 리소스로 폴백) | None(활성 chat 리소스 없음)
    LlmConfigResolver = Callable[[int | None], "LlmConfig | None"]

_TEMPLATE_RE = re.compile(r"\{\{\s*([\w.\[\]\-]+)\s*\}\}")


class ExecutionContext:
    """단일 워크플로우 실행의 공유 런타임 상태."""

    def __init__(
        self,
        execution_id: str,
        input_data: dict[str, Any],
        user_id: int | None = None,
        *,
        rag_search: "RagSearch | None" = None,
        llm_config: "LlmConfig | None" = None,
        llm_config_resolver: "LlmConfigResolver | None" = None,
    ) -> None:
        self.execution_id = execution_id
        self.input_data: dict[str, Any] = input_data
        self.user_id: int | None = user_id
        # 주입된 외부 의존 (ADR-0019 §2) — 노드가 호출/사용.
        self.rag_search = rag_search
        # 기본 chat LlmConfig(resource 미지정 폴백) + per-node resource_id 리졸버.
        self.llm_config = llm_config
        self.llm_config_resolver = llm_config_resolver
        # node_id → output dict
        self._node_outputs: dict[str, dict[str, Any]] = {}
        # node_id → bool (condition 노드 결과)
        self._condition_results: dict[str, bool] = {}

    def llm_config_for(self, resource_id: int | None) -> "LlmConfig | None":
        """노드가 선택한 llm_resource_id → LlmConfig. 리졸버 우선, 없으면 기본 llm_config."""
        if self.llm_config_resolver is not None:
            cfg = self.llm_config_resolver(resource_id)
            if cfg is not None:
                return cfg
        return self.llm_config

    # ── 노드 출력 관리 ──
    def set_node_output(self, node_id: str, output: dict[str, Any]) -> None:
        self._node_outputs[node_id] = output

    def get_node_output(self, node_id: str) -> dict[str, Any]:
        return self._node_outputs.get(node_id, {})

    def set_condition_result(self, node_id: str, result: bool) -> None:
        self._condition_results[node_id] = result

    def get_condition_result(self, node_id: str) -> bool | None:
        return self._condition_results.get(node_id)

    # ── 템플릿 해석 ──
    def resolve(self, value: Any) -> Any:
        """`value` 안의 템플릿을 재귀 해석."""
        if isinstance(value, str):
            return self._resolve_string(value)
        if isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        return value

    def resolve_node_inputs(self, node_config: dict[str, Any]) -> dict[str, Any]:
        """노드 config dict의 모든 템플릿을 해석 — node.execute()의 `inputs` 인자."""
        return self.resolve(node_config)

    def _resolve_string(self, template: str) -> Any:
        matches = _TEMPLATE_RE.findall(template)
        if not matches:
            return template

        # 전체가 단일 placeholder → 원시 값 반환(타입 보존).
        if len(matches) == 1 and template.strip() == f"{{{{{matches[0]}}}}}":
            return self._lookup(matches[0])

        def replacer(m: re.Match) -> str:
            val = self._lookup(m.group(1))
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val) if val is not None else ""

        return _TEMPLATE_RE.sub(replacer, template)

    def _lookup(self, path: str) -> Any:
        parts = path.split(".")

        if parts[0] == "input":
            if len(parts) < 2:
                return self.input_data
            return self._deep_get(self.input_data, parts[1:])

        if parts[0] == "nodes" and len(parts) >= 3:
            node_id = parts[1]
            node_output = self._node_outputs.get(node_id, {})
            if len(parts) == 3:  # {{nodes.<id>.output}}
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
