"""[케이스 01 - basic] Resource 샘플

Resource = URI로 접근하는 읽기 전용 데이터 소스

Tool vs Resource 선택 기준:
  Tool     — AI가 능동적으로 호출, 부수 효과 가능 (쓰기·외부 API·상태 변경)
  Resource — URI를 알면 직접 참조, 읽기 전용, 부수 효과 없음
  → 설정값·참고 데이터처럼 "제공"하는 것은 Resource, "수행"하는 것은 Tool

URI 형식:
  고정:    memo://categories                (도메인://경로)
  템플릿:  memo://item/{memo_id}            (경로에 {변수명} 포함)

형태:
  1. 정적 Resource   — 항상 동일한 내용 반환 (설정, 가이드, 고정 목록)
  2. 동적 Resource   — 호출마다 현재 상태 계산 (실시간 통계, 현재 설정값)
  3. JSON Resource   — 구조화된 데이터를 JSON 문자열로 반환
  4. Template        — URI 변수 → 함수 파라미터 자동 전달, 개별 항목 조회

app.py 등록:
    from src.sample.basic import resources as basic_resources  # noqa: F401
"""
import json

from src.core.mcp import mcp


# 정적 Resource — 항상 동일한 내용 반환
# 설정값, 가이드 문서, 고정 목록처럼 변하지 않는 데이터에 적합
@mcp.resource("memo://categories")
def get_basic_categories() -> str:
    """사용 가능한 메모 카테고리 목록"""
    categories = ["일반", "업무", "개인", "아이디어", "TODO", "참고"]
    return "사용 가능한 카테고리:\n" + "\n".join(f"- {c}" for c in categories)


@mcp.resource("memo://guide")
def get_basic_guide() -> str:
    """메모 도구 사용 가이드"""
    return """
메모 관리 도구 가이드 (basic 샘플)
====================================
기초 도구 (PART 1):
  basic_hello(name)                              → 인사말 반환
  basic_type_demo(text, repeat?, ...)            → 타입 파라미터 예제
  basic_divide(numerator, denominator)           → 나누기 + ToolError

메모 CRUD 도구 (PART 2):
  basic_create_memo(title, content, category?)   → 메모 생성
  basic_get_memo(memo_id)                        → 단건 조회
  basic_list_memos(category?)                    → 목록 조회
  basic_update_memo(memo_id, title?, content?)   → 부분 수정
  basic_delete_memo(memo_id)                     → 삭제
  basic_get_memo_stats()                         → 통계

주의: 인메모리 저장소 — 서버 재시작 시 초기화됨
""".strip()


# 동적 Resource — 매 호출마다 현재 상태를 읽어 반환
# 정적 Resource와 달리 함수 실행 시점의 최신 데이터 반영
#
# 지역 import(함수 안에서 import)를 쓰는 이유:
#   resources.py 상단에 두면 tools.py ↔ resources.py 순환 임포트 오류 발생
#   함수 실행 시점에 임포트하면 모듈 로드 순서와 무관하게 안전
@mcp.resource("memo://live-stats")
def get_live_stats() -> str:
    """현재 저장된 메모 수 실시간 반환."""
    from src.sample.basic.tools import _store  # 순환 임포트 방지

    total = len(_store)
    categories: dict[str, int] = {}
    for memo in _store.values():
        categories[memo.category] = categories.get(memo.category, 0) + 1

    lines = [f"현재 메모 수: {total}개"]
    if categories:
        lines.append("카테고리별 분포:")
        for cat, count in sorted(categories.items()):
            lines.append(f"  - {cat}: {count}개")
    else:
        lines.append("(메모 없음)")

    return "\n".join(lines)


# JSON 형식 Resource — 구조화된 데이터를 JSON 문자열로 반환
# AI나 클라이언트가 파싱해서 사용하기 쉬운 형태 (str 반환이지만 내용은 JSON)
@mcp.resource("memo://schema")
def get_memo_schema() -> str:
    """Memo 데이터 구조를 JSON Schema 형식으로 반환."""
    schema = {
        "type": "object",
        "description": "메모 객체 구조",
        "properties": {
            "id":         {"type": "integer",  "description": "고유 식별자 (자동 생성)"},
            "title":      {"type": "string",   "description": "메모 제목 (필수, 공백 불가)"},
            "content":    {"type": "string",   "description": "메모 본문 (필수, 공백 불가)"},
            "category":   {"type": "string",   "description": "분류 태그 (기본값: 일반)"},
            "created_at": {"type": "string",   "description": "생성 시각 (ISO 8601 UTC)"},
            "updated_at": {"type": "string",   "description": "수정 시각 (ISO 8601 UTC)"},
        },
        "required": ["id", "title", "content", "category", "created_at", "updated_at"],
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


# Resource Template — URI 경로의 {변수명}이 함수 파라미터로 자동 전달
# 사용 예:
#   client.read_resource("memo://item/1")   → memo_id=1 로 호출
#   client.read_resource("memo://item/42")  → memo_id=42 로 호출
# Tool과 차이: Tool은 AI가 능동적으로 호출, Resource는 URI를 알면 클라이언트가 직접 참조
@mcp.resource("memo://item/{memo_id}")
def get_memo_resource(memo_id: int) -> str:
    """특정 메모를 URI로 직접 조회."""
    from src.sample.basic.tools import _store  # 순환 임포트 방지

    memo = _store.get(memo_id)
    if memo is None:
        return f"[오류] 메모 ID {memo_id}를 찾을 수 없습니다."

    return (
        f"ID: {memo.id}\n"
        f"제목: {memo.title}\n"
        f"카테고리: {memo.category}\n"
        f"내용: {memo.content}\n"
        f"생성: {memo.created_at}\n"
        f"수정: {memo.updated_at}"
    )
