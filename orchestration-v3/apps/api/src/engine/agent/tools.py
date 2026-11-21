"""샘플 도구 + 기본 레지스트리 (ADR-0008).

⚠️ 데모/골격용. 실제 도구(MCP 연동 등)는 도메인 이식 단계에서 교체·확장한다.
각 도구에 위험 티어를 붙여 승인 정책이 동작하는지 검증할 수 있게 한다.
"""

from __future__ import annotations

from typing import Any

from src.engine.agent.registry import RiskTier, ToolKind, ToolRegistry, ToolSpec


# ── 되묻기(ask_user) — 내장 INTERRUPT 도구 (ADR-0025 §2) ──
# 핸들러는 실행되지 않는다: 그래프 tools 노드가 INTERRUPT 도구를 특수 처리해 사용자 답변을
# 도구 결과(ToolMessage)로 주입한다. 데모 도구들과 달리 실모델에 bind되는 실제 능력이다.
def _ask_user_noop(**_kwargs: Any) -> str:  # pragma: no cover — 호출되지 않음
    return ""


ASK_USER_TOOL = ToolSpec(
    name="ask_user",
    description="필요한 핵심 정보가 부족할 때 사용자에게 되묻는다(실행 아님).",
    handler=_ask_user_noop,
    risk=RiskTier.AUTO,      # 부수효과 없음 — 승인 대상 아님
    kind=ToolKind.INTERRUPT,
)

# 실모델 bind_tools용 OpenAI 함수 스키마 (ADR-0025 §4). registry ToolSpec은 bind 불가라 별도 정의.
ASK_USER_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "ask_user",
        "description": (
            "요청을 수행하기에 핵심 정보(대상·기간·형식·범위 등)가 부족하면, 추측해서 답하지 말고 "
            "이 도구로 사용자에게 되묻는다. 짧고 구체적인 질문 1개를 하고, 선택지가 분명하면 options로 제시한다. "
            "정보가 충분하면 호출하지 말고 바로 답한다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "사용자에게 할 한 문장 질문(한국어)."},
                "options": {
                    "type": "array",
                    "description": "사용자가 고를 보기(선택적). 분명한 선택지가 있을 때만.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string", "description": "선택 시 모델에 전달될 값."},
                            "label": {"type": "string", "description": "사용자에게 보일 라벨."},
                        },
                        "required": ["value", "label"],
                    },
                },
                "allow_free_text": {
                    "type": "boolean",
                    "description": "자유 입력 허용 여부(기본 true). 보기 중 하나만 받으려면 false.",
                },
            },
            "required": ["question"],
        },
    },
}


def interrupt_tool_schemas() -> list[dict[str, Any]]:
    """실모델에 bind할 INTERRUPT 도구 스키마 목록 (ADR-0025). 현재 ask_user 1종."""
    return [ASK_USER_SCHEMA]


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
    """데모 기본 레지스트리. 티어별 대표 도구 + 되묻기(ask_user, ADR-0025)."""
    return ToolRegistry(
        [
            ASK_USER_TOOL,  # 되묻기 — 실모델에 bind되는 내장 능력 (ADR-0025)
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
