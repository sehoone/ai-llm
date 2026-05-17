"""
[케이스 01 - basic] Resource 샘플

━━━ MCP Resource란? ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Resource = URI(주소)로 접근하는 읽기 전용 데이터 소스

  Tool vs Resource 선택 기준:
    ┌──────────────┬──────────────────────────────────┬─────────────────────┐
    │              │  Tool                            │  Resource           │
    ├──────────────┼──────────────────────────────────┼─────────────────────┤
    │  부수 효과   │  가능 (쓰기, 외부 API 호출)       │  불가 (읽기 전용)    │
    │  호출 방식   │  AI가 능동적으로 call_tool()      │  URI로 read_resource│
    │  용도        │  작업 수행                        │  참고 데이터 제공   │
    │  예시        │  메모 생성, 환율 조회             │  카테고리 목록, 스키마│
    └──────────────┴──────────────────────────────────┴─────────────────────┘

  Resource의 3가지 형태:
    1. 정적 Resource   : 항상 동일한 내용 반환 (설정, 가이드 문서)
    2. 동적 Resource   : 호출마다 현재 상태 계산 (실시간 통계)
    3. Resource Template: URI에 변수 포함 ({param}) → 개별 항목 조회

━━━ URI 형식 규칙 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  고정 URI     : {도메인}://{경로}            예) memo://categories
  템플릿 URI   : {도메인}://{경로}/{변수}      예) memo://item/{memo_id}

다루는 패턴:
  - @mcp.resource("URI") 등록
  - 반환 타입: str (가장 일반적), bytes, JSON 문자열
  - AI가 tool 호출 전 컨텍스트로 참고하거나
    클라이언트가 read_resource()로 직접 조회
"""
import json

from src.core.mcp import mcp


# ── 형태 1: 정적 Resource — 항상 동일한 내용 ─────────────────────────────────
# 설정값, 가이드 문서, 고정 목록처럼 변하지 않는 데이터에 적합합니다.

@mcp.resource("memo://categories")
def get_basic_categories() -> str:
    """사용 가능한 메모 카테고리 목록 (정적 Resource 예시)"""
    categories = ["일반", "업무", "개인", "아이디어", "TODO", "참고"]
    return "사용 가능한 카테고리:\n" + "\n".join(f"- {c}" for c in categories)


@mcp.resource("memo://guide")
def get_basic_guide() -> str:
    """메모 도구 사용 가이드 (정적 Resource 예시)"""
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


# ── 형태 2: 동적 Resource — 호출 시마다 현재 상태 계산 ──────────────────────
# 함수 안에서 실시간 데이터를 읽어 반환합니다.
# 정적 변수와 달리 매 호출마다 최신 값을 보여줍니다.
#
# 주의: 지역 임포트(import inside function)를 쓰는 이유
#   → resources.py 와 tools.py 가 서로 임포트하면 순환 임포트 오류 발생
#   → 함수 실행 시점에 임포트하면 모듈 로드 순서와 무관하게 안전

@mcp.resource("memo://live-stats")
def get_live_stats() -> str:
    """현재 저장된 메모 수를 실시간으로 반환하는 동적 Resource.

    정적 Resource와 달리 매 호출마다 최신 상태를 반영합니다.
    실시간 카운트, 현재 설정값, 서버 상태 등을 노출할 때 사용합니다.
    """
    from src.sample.basic.tools import _store  # 순환 임포트 방지용 지역 임포트

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


# ── 형태 3: JSON 형식 Resource ────────────────────────────────────────────────
# 구조화된 데이터를 JSON 문자열로 반환합니다.
# AI나 클라이언트가 파싱해서 사용하기 쉬운 형태입니다.

@mcp.resource("memo://schema")
def get_memo_schema() -> str:
    """Memo 데이터 구조를 JSON Schema 형식으로 반환하는 Resource.

    AI가 메모 생성 도구를 쓰기 전에 이 Resource를 참조해
    어떤 필드가 필요한지 파악할 수 있습니다.
    """
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


# ── 형태 4: Resource Template — URI에 변수 포함 ──────────────────────────────
# URI 경로에 {변수명}을 넣으면 함수 파라미터로 자동 전달됩니다.
#
# 사용 예:
#   client.read_resource("memo://item/1")   → memo_id=1
#   client.read_resource("memo://item/42")  → memo_id=42
#
# Tool과의 차이: Tool은 AI가 능동적으로 호출, Resource는 URI를 알면 직접 참조 가능

@mcp.resource("memo://item/{memo_id}")
def get_memo_resource(memo_id: int) -> str:
    """특정 메모를 URI로 직접 조회하는 Resource Template.

    AI나 클라이언트가 memo_id를 URI에 직접 넣어 단건 조회합니다.
    read_resource("memo://item/1") 처럼 사용합니다.

    Args:
        memo_id: URI 경로에서 추출된 메모 ID
    """
    from src.sample.basic.tools import _store  # 순환 임포트 방지용 지역 임포트

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
