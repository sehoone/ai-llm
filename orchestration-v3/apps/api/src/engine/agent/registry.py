"""도구 레지스트리 + 위험 메타데이터 (ADR-0008 §1).

`engine`은 HTTP·domains를 모른다(ADR-0005). 도구의 위험도(`risk`)는 AI 능력의 속성이므로
여기(engine/agent)에 둔다. "누가 승인하는가"(인가·영속)는 domains/chat가 소유한다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class RiskTier(StrEnum):
    """도구 실행의 위험 티어 (ADR-0008 §1)."""

    AUTO = "AUTO"        # 읽기·안전 — 사용자 승인 없이 실행
    CONFIRM = "CONFIRM"  # 부수효과·비가역·범위초과 — 실행 전 승인 필요
    BLOCK = "BLOCK"      # 노출 금지 — 챗에서 호출 불가


# 티어 서열 (승격 비교용 — 큰 값일수록 엄격). 정책은 승격만 허용, 강등 금지.
_SEVERITY = {RiskTier.AUTO: 0, RiskTier.CONFIRM: 1, RiskTier.BLOCK: 2}


def stricter(a: RiskTier, b: RiskTier) -> RiskTier:
    """두 티어 중 더 엄격한(높은 서열) 쪽을 반환."""
    return a if _SEVERITY[a] >= _SEVERITY[b] else b


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """등록된 도구 1개의 정의 + 위험 메타데이터.

    - `risk`: 기본 티어. 명시 안 하면 보수적으로 `CONFIRM`(ADR-0008 §1).
    - `allow_edit`: `CONFIRM` 승인 시 사용자의 인자 수정 허용 여부. 파괴적·비가역 도구는 False.
    - `escalate_when`: 인자 기반 **승격** 술어. 참이면 티어를 최소 `CONFIRM`으로 올린다(강등 불가).
    """

    name: str
    description: str
    handler: Callable[..., Any]
    risk: RiskTier = RiskTier.CONFIRM
    allow_edit: bool = True
    escalate_when: Callable[[dict[str, Any]], bool] | None = None

    def effective_risk(self, args: dict[str, Any]) -> RiskTier:
        """인자를 반영한 실효 티어. `escalate_when`은 승격만 한다."""
        tier = self.risk
        if self.escalate_when is not None and self.escalate_when(args):
            tier = stricter(tier, RiskTier.CONFIRM)
        return tier


class ToolRegistry:
    """도구 이름 → ToolSpec 매핑. 챗/에이전트가 공유하는 단일 출처."""

    def __init__(self, specs: list[ToolSpec] | None = None) -> None:
        self._tools: dict[str, ToolSpec] = {}
        for spec in specs or []:
            self.register(spec)

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.name in self._tools:
            raise ValueError(f"중복 도구 등록: {spec.name}")
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def exposed(self) -> list[ToolSpec]:
        """챗에 노출 가능한 도구(BLOCK 제외)."""
        return [s for s in self._tools.values() if s.risk is not RiskTier.BLOCK]
