"""[케이스 01 - basic] Prompt 샘플

Prompt = 서버에 저장한 프롬프트 템플릿
  클라이언트(앱, Claude Desktop 등)가 get_prompt()로 가져와 AI 대화에 주입
  Tool이 "AI가 실행하는 함수"라면, Prompt는 "AI가 어떤 맥락으로 시작할지 설정"

Prompt vs 직접 메시지 차이:
  직접 메시지 — 사용자가 채팅창에 매번 긴 지시문 타이핑
  Prompt      — 서버에 저장된 템플릿, 파라미터만 바꿔 재사용 가능

반환 타입:
  str           → 단일 user 메시지로 자동 변환
  list[Message] → role 있는 멀티 메시지 (few-shot 예시 주입에 활용)

사용 흐름:
  1. 클라이언트: client.get_prompt("memo_organize", {"category": "업무"})
  2. 서버: 파라미터 대입 후 메시지 반환
  3. 클라이언트: 반환된 메시지를 AI 대화에 주입 → AI가 해당 맥락으로 작업 시작

app.py 등록:
    from src.sample.basic import prompts as basic_prompts  # noqa: F401
"""
from fastmcp.prompts.base import Message

from src.core.mcp import mcp


# 파라미터 없는 단순 프롬프트 — str 반환 → user 메시지 하나로 자동 변환
@mcp.prompt()
def memo_summary() -> str:
    """전체 메모 요약 요청 프롬프트."""
    return (
        "저장된 메모 전체를 조회한 뒤, 카테고리별로 분류하고 "
        "각 메모의 핵심 내용을 한 줄로 요약해 주세요. "
        "오늘 처리해야 할 TODO 항목이 있으면 별도로 강조해 주세요."
    )


# 파라미터 있는 동적 프롬프트 — f-string으로 값 삽입
# 같은 템플릿 구조를 카테고리마다 재사용 가능
@mcp.prompt()
def memo_organize(category: str) -> str:
    """특정 카테고리 메모 정리 요청 프롬프트.

    Args:
        category: 정리할 카테고리 이름 (예: 업무, 개인)
    """
    return (
        f"'{category}' 카테고리의 메모를 모두 조회하세요. "
        "중복이나 오래된 항목은 삭제를 제안하고, "
        "관련 내용끼리 묶어 정리 방안을 제시해 주세요."
    )


# 멀티 메시지 프롬프트 — list[Message] 반환으로 role 지정 가능
# assistant 메시지를 포함하면 AI가 특정 형식으로 계속 응답하도록 유도 (few-shot)
#
# Message(role="user", content="...")      → 사용자 메시지
# Message(role="assistant", content="...") → AI 사전 응답 (few-shot 예시)
@mcp.prompt()
def memo_create_guide(topic: str) -> list[Message]:
    """메모 생성 안내 멀티 메시지 프롬프트 (few-shot 포함).

    Args:
        topic: 메모를 작성할 주제 (예: "오늘 할 일", "프로젝트 아이디어")
    """
    return [
        Message(
            content=(
                f"'{topic}'에 대한 메모를 작성하려고 합니다. "
                "먼저 basic_list_memos()로 기존 메모를 확인하고, "
                "비슷한 내용이 있다면 업데이트를 제안해 주세요. "
                "없다면 basic_create_memo()로 새 메모를 만들어 주세요."
            ),
            role="user",
        ),
        Message(
            content=(
                f"네, '{topic}' 관련 메모를 확인하겠습니다. "
                "먼저 전체 메모 목록을 조회한 뒤 관련 항목을 찾아볼게요."
            ),
            role="assistant",
        ),
    ]


# 구조화된 리포트 요청 — 긴 지시문을 서버에 저장해두고 파라미터로 커스터마이즈
# 클라이언트 코드에 긴 프롬프트를 하드코딩하지 않아도 됨
@mcp.prompt()
def memo_weekly_report(user_name: str = "사용자") -> str:
    """주간 메모 리포트 요청 프롬프트.

    Args:
        user_name: 리포트 수신자 이름
    """
    return f"""
{user_name}님의 주간 메모 리포트를 작성해 주세요.

다음 순서로 진행하세요:
1. basic_list_memos()로 전체 메모 목록 조회
2. basic_get_memo_stats()로 카테고리별 통계 확인
3. 아래 형식으로 리포트 작성:

---
## {user_name}님 주간 메모 리포트

### 전체 현황
- 총 메모 수: X개
- 카테고리별 분포: ...

### 카테고리별 요약
#### 업무
- ...

#### TODO
- 완료 필요 항목: ...

### 권장 액션
- 정리가 필요한 메모: ...
- 삭제 고려 항목: ...
---
""".strip()
