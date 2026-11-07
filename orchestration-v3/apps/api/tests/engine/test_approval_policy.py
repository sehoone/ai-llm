"""승인 정책 엔진 단위 테스트 (ADR-0008 §1). 순수 로직 — 외부 의존 없음."""

from src.engine.agent.policy import ApprovalPolicy, Decision, PolicyContext, ToolCall
from src.engine.agent.registry import RiskTier, ToolRegistry, ToolSpec

USER = PolicyContext(role="USER")


def _registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ToolSpec("search", "읽기", handler=lambda **_: "ok", risk=RiskTier.AUTO),
            ToolSpec("send_email", "쓰기", handler=lambda **_: "ok", risk=RiskTier.CONFIRM),
            ToolSpec("danger", "차단", handler=lambda **_: "ok", risk=RiskTier.BLOCK),
            ToolSpec(
                "charge",
                "결제",
                handler=lambda **_: "ok",
                risk=RiskTier.AUTO,
                escalate_when=lambda a: int(a.get("amount", 0)) > 100_000,
            ),
        ]
    )


def _policy() -> ApprovalPolicy:
    return ApprovalPolicy(_registry())


def test_auto_tool_allows_without_confirmation() -> None:
    r = _policy().evaluate(ToolCall("1", "search", {"q": "hi"}), USER)
    assert r.decision is Decision.ALLOW


def test_sideeffect_tool_requires_confirmation() -> None:
    r = _policy().evaluate(ToolCall("1", "send_email", {"to": "a@b.c"}), USER)
    assert r.decision is Decision.CONFIRM


def test_blocked_tool_is_denied() -> None:
    r = _policy().evaluate(ToolCall("1", "danger", {}), USER)
    assert r.decision is Decision.BLOCK


def test_unknown_tool_is_denied_by_default() -> None:
    r = _policy().evaluate(ToolCall("1", "nonexistent", {}), USER)
    assert r.decision is Decision.BLOCK


def test_runtime_predicate_escalates_auto_to_confirm() -> None:
    policy = _policy()
    small = policy.evaluate(ToolCall("1", "charge", {"amount": 1000}), USER)
    big = policy.evaluate(ToolCall("2", "charge", {"amount": 500_000}), USER)
    assert small.decision is Decision.ALLOW
    assert big.decision is Decision.CONFIRM


def test_role_override_auto_approves_confirm_tool() -> None:
    ctx = PolicyContext(role="ADMIN", auto_approve_tools=frozenset({"send_email"}))
    r = _policy().evaluate(ToolCall("1", "send_email", {"to": "a@b.c"}), ctx)
    assert r.decision is Decision.ALLOW
