"""샘플 도구 + 기본 레지스트리 (ADR-0008).

⚠️ 데모/골격용. 실제 도구(MCP 연동 등)는 도메인 이식 단계에서 교체·확장한다.
각 도구에 위험 티어를 붙여 승인 정책이 동작하는지 검증할 수 있게 한다.
"""

from __future__ import annotations

from src.engine.agent.registry import RiskTier, ToolRegistry, ToolSpec


def _search_docs(query: str) -> str:
    """읽기 전용 — 승인 불필요(AUTO)."""
    return f"'{query}' 검색 결과(샘플): 관련 문서 3건."


def _send_email(to: str, subject: str, body: str) -> str:
    """외부 쓰기·부수효과 — 승인 필요(CONFIRM)."""
    return f"메일 발송 완료 → {to} (제목: {subject})"


def _delete_resource(resource_id: int) -> str:
    """파괴적·비가역 — 승인 필요 + 인자 수정 금지(allow_edit=False)."""
    return f"리소스 {resource_id} 삭제 완료"


def _charge(amount: int) -> str:
    """고비용 — 금액이 크면 승격(escalate_when)."""
    return f"{amount}원 결제 완료"


def default_registry() -> ToolRegistry:
    """데모 기본 레지스트리. 티어별 대표 도구 포함."""
    return ToolRegistry(
        [
            ToolSpec(
                name="search_docs",
                description="문서를 검색한다(읽기 전용).",
                handler=_search_docs,
                risk=RiskTier.AUTO,
            ),
            ToolSpec(
                name="send_email",
                description="메일을 발송한다.",
                handler=_send_email,
                risk=RiskTier.CONFIRM,
                allow_edit=True,
            ),
            ToolSpec(
                name="delete_resource",
                description="리소스를 영구 삭제한다.",
                handler=_delete_resource,
                risk=RiskTier.CONFIRM,
                allow_edit=False,  # 비가역 — 인자 수정 금지
            ),
            ToolSpec(
                name="charge",
                description="결제를 수행한다.",
                handler=_charge,
                risk=RiskTier.AUTO,
                # 10만원 초과 결제는 AUTO→CONFIRM 승격 (런타임 술어)
                escalate_when=lambda args: int(args.get("amount", 0)) > 100_000,
            ),
        ]
    )
