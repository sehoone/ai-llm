"""[케이스 01 - basic] 인메모리 메모 관리 + MCP Tool 기초

MCP primitive:
  Tool      — AI가 직접 호출하는 함수 (읽기·쓰기·외부 API 모두 가능)
  Resource  — URI로 노출하는 읽기 전용 데이터
  Prompt    — 클라이언트가 get_prompt()로 가져오는 프롬프트 템플릿

Tool 등록 흐름:
  1. @mcp.tool() 데코레이터 → FastMCP에 함수 등록
  2. FastMCP가 파라미터 이름·타입힌트·docstring으로 JSON Schema 자동 생성
  3. AI(Claude 등)가 Schema 읽고 언제·어떻게 호출할지 결정
  4. 반환값은 JSON 직렬화 가능한 타입 모두 허용 (str, dict, list, int …)

구성:
  PART 1 — Tool 기초: basic_hello / basic_type_demo / basic_divide
  PART 2 — 메모 CRUD: create / get / list / update / delete / stats
           패턴: @tool_logger 조합 / Pydantic .model_dump() / model_copy 부분 수정

app.py 등록:
    from src.sample.basic import tools as basic_tools  # noqa: F401
"""
from datetime import datetime, timezone
from typing import Any, Optional

from fastmcp.exceptions import ToolError

from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp
from src.sample.basic.models import Memo, MemoListResponse, MemoStatsResponse

logger = get_logger("sample.basic")


# ── PART 1: Tool 기초 예제 ────────────────────────────────────────────────────

# @mcp.tool() 로 등록된 함수:
#   - 파라미터 타입힌트 → JSON Schema 자동 생성 (AI가 어떤 값을 넣을지 이 Schema로 판단)
#   - docstring 첫 줄 → AI에게 보이는 도구 설명
#   - 반환값 → dict 아니어도 OK, JSON 직렬화 가능하면 모두 허용
@mcp.tool()
async def basic_hello(name: str) -> str:
    """이름을 받아 인사말 반환 — @mcp.tool() 최소 예제."""
    return f"안녕하세요, {name}님! MCP Tool이 정상 작동합니다."


# Python 타입힌트 → JSON Schema 변환 (FastMCP가 자동으로 처리):
#   str         → "type": "string"    텍스트 입력
#   int         → "type": "integer"   정수 입력
#   float       → "type": "number"    소수 포함 숫자
#   bool        → "type": "boolean"   true / false
#   Optional[X] → required에서 제외   생략 가능한 파라미터
#   기본값(= 값) 있으면 선택적, 없으면 필수
@mcp.tool()
async def basic_type_demo(
    text: str,
    repeat: int = 1,
    multiplier: float = 1.0,
    uppercase: bool = False,
    prefix: Optional[str] = None,
) -> dict[str, Any]:
    """다양한 파라미터 타입 예제.

    Args:
        text: 처리할 텍스트 (str, 필수)
        repeat: 반복 횟수 (int, 기본값 1)
        multiplier: 예시용 부동소수점 숫자 (float, 기본값 1.0)
        uppercase: 대문자 변환 여부 (bool, 기본값 False)
        prefix: 결과 앞에 붙일 문자열 (Optional[str], 생략 가능)

    Returns:
        처리 결과와 입력값을 담은 딕셔너리
    """
    result = text * max(1, repeat)
    if uppercase:
        result = result.upper()
    if prefix:
        result = f"{prefix} {result}"

    return {
        "result": result,
        "received": {
            "text": text,
            "repeat": repeat,
            "multiplier": multiplier,
            "uppercase": uppercase,
            "prefix": prefix,
        },
    }


# ToolError vs Exception — 반드시 구분해서 사용:
#   ToolError  → AI가 에러 메시지를 읽고 다른 값으로 재시도하거나 사용자에게 안내 가능
#              → 스택트레이스 없이 깔끔한 메시지만 클라이언트에 전달
#   Exception  → 서버 500 에러 + 스택트레이스, AI가 원인을 알 수 없어 재시도 불가
# 예상 가능한 실패(잘못된 입력, 리소스 없음 등)는 항상 ToolError
@mcp.tool()
async def basic_divide(numerator: float, denominator: float) -> dict[str, Any]:
    """두 수 나누기 — ToolError 사용법 예제.

    Args:
        numerator: 분자
        denominator: 분모 (0이면 ToolError 발생)

    Returns:
        { numerator, denominator, result, remainder }
    """
    if denominator == 0:
        raise ToolError("0으로 나눌 수 없습니다. 분모에 0이 아닌 값을 입력하세요.")

    return {
        "numerator": numerator,
        "denominator": denominator,
        "result": numerator / denominator,
        "remainder": numerator % denominator if isinstance(numerator, int) and isinstance(denominator, int) else None,
    }


# ── PART 2: 실전 패턴 — 메모 CRUD ────────────────────────────────────────────
# 인메모리 저장소 — 서버 재시작 시 초기화됨
# 추가로 다루는 패턴:
#   @tool_logger: 실행 로그 자동 기록 (tool_start / tool_done / tool_error)
#   .model_dump(): Pydantic 모델 → dict 변환 (MCP 응답은 JSON 직렬화 가능해야 함)
#   model_copy(update={...}): 불변 모델의 일부 필드만 교체
#   MemoListResponse: 여러 항목을 묶는 복합 응답 모델
_store: dict[int, Memo] = {}
_next_id: int = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# 데코레이터 적용 순서 (위 → 아래 = 바깥 → 안쪽):
#   @mcp.tool()       ← FastMCP가 이 함수를 MCP tool로 등록
#   @tool_logger(...) ← 실행 시 로그를 남기는 래퍼
#   async def fn():   ← 실제 비즈니스 로직
# 순서가 바뀌면 @tool_logger 자체가 tool로 등록되거나 로그가 누락됨
@mcp.tool()
@tool_logger(logger, param_keys=["title", "category"])
async def basic_create_memo(title: str, content: str, category: str = "일반") -> dict[str, Any]:
    """새 메모 작성.

    Args:
        title: 메모 제목 (공백 불가)
        content: 메모 본문 (공백 불가)
        category: 분류 태그 (기본값: 일반)

    Returns:
        생성된 Memo 딕셔너리

    Raises:
        ToolError: 제목·본문이 비어있을 때
    """
    global _next_id

    if not title.strip():
        raise ToolError("제목은 비울 수 없습니다.")
    if not content.strip():
        raise ToolError("본문은 비울 수 없습니다.")

    now = _now()
    memo = Memo(
        id=_next_id,
        title=title.strip(),
        content=content.strip(),
        category=category.strip() or "일반",
        created_at=now,
        updated_at=now,
    )
    _store[_next_id] = memo
    _next_id += 1

    return memo.model_dump()  # Pydantic 모델 → dict (MCP 응답에 필요)


@mcp.tool()
@tool_logger(logger, param_keys=["memo_id"])
async def basic_get_memo(memo_id: int) -> dict[str, Any]:
    """ID로 메모 조회.

    Args:
        memo_id: 조회할 메모 ID

    Returns:
        Memo 딕셔너리

    Raises:
        ToolError: 해당 ID 메모가 없을 때
    """
    memo = _store.get(memo_id)
    if memo is None:
        raise ToolError(f"메모 ID {memo_id}를 찾을 수 없습니다.")
    return memo.model_dump()


@mcp.tool()
@tool_logger(logger, param_keys=["category"])
async def basic_list_memos(category: Optional[str] = None) -> dict[str, Any]:
    """메모 목록 조회.

    Args:
        category: 필터링 카테고리 — 생략하면 전체 반환

    Returns:
        { total: int, memos: [...] }
    """
    memos = list(_store.values())
    if category:
        memos = [m for m in memos if m.category == category]

    return MemoListResponse(total=len(memos), memos=memos).model_dump()


@mcp.tool()
@tool_logger(logger, param_keys=["memo_id"])
async def basic_update_memo(
    memo_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None,
) -> dict[str, Any]:
    """메모 부분 수정 — 전달한 필드만 변경.

    Args:
        memo_id: 수정할 메모 ID
        title: 새 제목 (생략하면 기존 값 유지)
        content: 새 본문 (생략하면 기존 값 유지)
        category: 새 카테고리 (생략하면 기존 값 유지)

    Returns:
        수정된 Memo 딕셔너리
    """
    memo = _store.get(memo_id)
    if memo is None:
        raise ToolError(f"메모 ID {memo_id}를 찾을 수 없습니다.")

    # model_copy(update={...}) — Pydantic 모델을 직접 수정하지 않고 새 객체 반환
    # None 체크 후 전달된 값만 교체, 나머지는 기존 값 유지
    updated = memo.model_copy(
        update={
            "title": title.strip() if title else memo.title,
            "content": content.strip() if content else memo.content,
            "category": category.strip() if category else memo.category,
            "updated_at": _now(),
        }
    )
    _store[memo_id] = updated
    return updated.model_dump()


@mcp.tool()
@tool_logger(logger, param_keys=["memo_id"])
async def basic_delete_memo(memo_id: int) -> dict[str, Any]:
    """메모 삭제.

    Returns:
        { deleted: bool, id: int, title: str }
    """
    memo = _store.pop(memo_id, None)
    if memo is None:
        raise ToolError(f"메모 ID {memo_id}를 찾을 수 없습니다.")
    return {"deleted": True, "id": memo_id, "title": memo.title}


@mcp.tool()
@tool_logger(logger, param_keys=[])
async def basic_get_memo_stats() -> dict[str, Any]:
    """카테고리별 메모 통계 반환.

    Returns:
        { total: int, categories: { 카테고리명: 개수 } }
    """
    categories: dict[str, int] = {}
    for memo in _store.values():
        categories[memo.category] = categories.get(memo.category, 0) + 1

    return MemoStatsResponse(total=len(_store), categories=categories).model_dump()
