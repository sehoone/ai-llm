"""승인 정책 엔진 (ADR-0008 §1) — 순수 함수, HTTP·DB·domains 비의존.

입력: 도구 호출(`ToolCall`) + 컨텍스트(`PolicyContext`, 도메인이 값으로 주입).
출력: `PolicyResult`(ALLOW | CONFIRM | BLOCK). 테스트는 외부 의존 없이 가능하다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from src.engine.agent.registry import RiskTier, ToolRegistry


@dataclass(frozen=True, slots=True)
class ToolCall:
    """LLM이 요청한 단일 도구 호출."""

    id: str
    name: str
    args: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PolicyContext:
    """승인 판단 컨텍스트. 도메인이 역할·오버라이드를 해석해 값으로 주입(ADR-0005 §4).

    - `role`: 요청 사용자의 역할 문자열(engine은 `User`를 모른다).
    - `auto_approve_tools`: 이 호출자에 한해 `CONFIRM`을 면제할 도구 이름들(역할 기반 오버라이드).
    """

    role: str = "USER"
    auto_approve_tools: frozenset[str] = field(default_factory=frozenset)


class Decision(StrEnum):
    ALLOW = "ALLOW"      # 바로 실행
    CONFIRM = "CONFIRM"  # 사용자 승인 대기
    BLOCK = "BLOCK"      # 실행 거부


@dataclass(frozen=True, slots=True)
class PolicyResult:
    decision: Decision
    tier: RiskTier
    allow_edit: bool
    reason: str


class ApprovalPolicy:
    """도구 레지스트리 + 컨텍스트로 승인 결정을 내린다 (ADR-0008 §1)."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def evaluate(self, call: ToolCall, ctx: PolicyContext) -> PolicyResult:
        spec = self._registry.get(call.name)

        # 미등록 도구 = 기본 거부 (ADR-0008 §1).
        if spec is None:
            return PolicyResult(Decision.BLOCK, RiskTier.BLOCK, False, f"미등록 도구: {call.name}")

        tier = spec.effective_risk(call.args)  # escalate_when 반영 (승격만)

        if tier is RiskTier.BLOCK:
            return PolicyResult(Decision.BLOCK, tier, False, f"차단된 도구: {call.name}")

        if tier is RiskTier.AUTO:
            return PolicyResult(Decision.ALLOW, tier, spec.allow_edit, "읽기·안전 작업")

        # CONFIRM — 역할/사용자 오버라이드로 면제 가능.
        if call.name in ctx.auto_approve_tools:
            return PolicyResult(
                Decision.ALLOW, tier, spec.allow_edit, f"{ctx.role} 오버라이드로 자동 승인"
            )

        reason = "승격됨(인자 조건)" if tier != spec.risk else "부수효과 — 승인 필요"
        return PolicyResult(Decision.CONFIRM, tier, spec.allow_edit, reason)
