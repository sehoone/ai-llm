"""
[케이스 01 - basic] 인메모리 메모 관리 + MCP Tool 기초 개념 — 외부 의존성 없음

━━━ MCP의 3가지 핵심 Primitive ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Tool      | AI가 직접 호출하는 함수. 읽기·쓰기·외부 API 호출 모두 가능.
  Resource  | URI로 노출하는 읽기 전용 데이터. AI가 컨텍스트로 참조.
  Prompt    | AI에게 주입할 프롬프트 템플릿. 클라이언트가 get_prompt()로 요청.

━━━ Tool 동작 원리 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. @mcp.tool() 데코레이터로 함수를 등록
  2. FastMCP가 파라미터 이름·타입 힌트·docstring으로 JSON Schema 자동 생성
  3. AI(Claude 등)가 이 Schema를 읽고 언제·어떻게 호출할지 결정
  4. 반환값은 JSON 직렬화 가능한 모든 타입 허용 (str, dict, list, int …)

━━━ 이 파일의 구성 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  PART 1 — Tool 기초 개념 (초보자용 단계별 예제)
    basic_hello          : 가장 단순한 Tool — 문자열 반환
    basic_type_demo      : 파라미터 타입 종류 (str, int, float, bool, Optional)
    basic_divide         : 입력 검증과 ToolError 사용법

  PART 2 — 실전 패턴 (메모 CRUD)
    @tool_logger 조합 순서, Pydantic 모델 반환, 부분 수정(model_copy) 등

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


# ═══════════════════════════════════════════════════════════════════════════════
# PART 1: Tool 기초 개념 — 초보자용 단계별 예제
# ═══════════════════════════════════════════════════════════════════════════════

# ── 단계 1: Hello World — 가장 단순한 Tool ───────────────────────────────────
# @mcp.tool() 하나로 AI가 호출 가능한 함수가 됩니다.
# 반환 타입은 str, int, list, dict 등 JSON 직렬화 가능하면 모두 OK.
# dict가 아니어도 됩니다.

@mcp.tool()
async def basic_hello(name: str) -> str:
    """이름을 받아 인사말을 반환하는 MCP Tool 최소 예제.

    이 Tool은 MCP의 가장 단순한 형태를 보여줍니다:
      - @mcp.tool() 데코레이터 한 줄로 등록 완료
      - 파라미터(name)와 타입 힌트(str)가 AI에게 보이는 스키마
      - docstring이 AI가 읽는 도구 설명서

    Args:
        name: 인사할 대상 이름

    Returns:
        인사말 문자열
    """
    return f"안녕하세요, {name}님! MCP Tool이 정상 작동합니다.!"


# ── 단계 2: 파라미터 타입 종류 ──────────────────────────────────────────────
# Python 타입 힌트 → AI에게 전달되는 JSON Schema 타입으로 자동 변환됩니다.
#
#   Python 타입       JSON Schema type         AI 동작
#   str             → "type": "string"       → 텍스트 입력
#   int             → "type": "integer"      → 정수 입력
#   float           → "type": "number"       → 소수점 포함 숫자
#   bool            → "type": "boolean"      → true/false
#   Optional[X]     → required: false        → 생략 가능한 파라미터

@mcp.tool()
async def basic_type_demo(
    text: str,
    repeat: int = 1,
    multiplier: float = 1.0,
    uppercase: bool = False,
    prefix: Optional[str] = None,
) -> dict[str, Any]:
    """다양한 파라미터 타입을 보여주는 예제 Tool.

    AI는 각 파라미터의 타입을 보고 어떤 값을 넣어야 할지 판단합니다.
    기본값(= 값)이 있으면 선택적 파라미터, 없으면 필수 파라미터입니다.

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


# ── 단계 3: 입력 검증과 ToolError ───────────────────────────────────────────
# 예상된 실패(잘못된 입력, 찾을 수 없음 등)는 반드시 ToolError를 사용하세요.
#
#   ToolError vs 일반 Exception 차이:
#     ToolError    → AI가 "도구 호출 실패, 메시지: X" 로 인식하고 대응 가능
#     Exception    → 서버 500 에러, stack trace 발생, AI가 이유를 모름
#
#   ToolError는 클라이언트에게 스택 트레이스 없이 깔끔한 에러 메시지만 전달합니다.

@mcp.tool()
async def basic_divide(numerator: float, denominator: float) -> dict[str, Any]:
    """두 수를 나누는 Tool — ToolError 사용법을 보여줍니다.

    0으로 나누기처럼 예상 가능한 실패에는 ToolError를 사용하세요.
    AI는 ToolError 메시지를 읽고 다른 값으로 재시도하거나 사용자에게 안내합니다.

    Args:
        numerator: 분자 (나눌 수)
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


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2: 실전 패턴 — 메모 CRUD (인메모리 저장소)
# ═══════════════════════════════════════════════════════════════════════════════
# 여기서 다루는 추가 패턴:
#   ① @mcp.tool() + @tool_logger 데코레이터 조합 순서
#   ② Pydantic 모델 → .model_dump() dict 반환
#   ③ 부분 수정: model_copy(update={...})
#   ④ 복합 응답 모델 (MemoListResponse, MemoStatsResponse)
# ═══════════════════════════════════════════════════════════════════════════════

# 인메모리 저장소 — 서버 재시작 시 초기화됨
_store: dict[int, Memo] = {}
_next_id: int = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# 포인트 ①: 데코레이터 적용 순서
#   @mcp.tool()      ← 가장 바깥 (FastMCP가 함수를 tool로 등록)
#   @tool_logger(...)← 안쪽 (실행 로그를 감싸는 래퍼)
#   async def fn():  ← 실제 함수
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
@tool_logger(logger, param_keys=["title", "category"])
async def basic_create_memo(title: str, content: str, category: str = "일반") -> dict[str, Any]:
    """새 메모를 작성합니다.

    Args:
        title: 메모 제목 (필수, 공백 불가)
        content: 메모 본문 (필수, 공백 불가)
        category: 분류 태그 (기본값: 일반)

    Returns:
        생성된 Memo 딕셔너리

    Raises:
        ToolError: 제목·본문이 비어있을 때
    """
    global _next_id

    # 포인트 ②: 입력 검증은 ToolError로 — MCP 프로토콜 수준 에러 반환
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

    # 포인트 ③: Pydantic → dict 변환 후 반환
    return memo.model_dump()


@mcp.tool()
@tool_logger(logger, param_keys=["memo_id"])
async def basic_get_memo(memo_id: int) -> dict[str, Any]:
    """ID로 메모를 조회합니다.

    Args:
        memo_id: 조회할 메모 ID

    Raises:
        ToolError: 해당 ID 메모가 없을 때 (404 상황)
    """
    memo = _store.get(memo_id)
    if memo is None:
        # 포인트 ④: 찾을 수 없음 → ToolError (warning 레벨 로그, stack trace 없음)
        raise ToolError(f"메모 ID {memo_id}를 찾을 수 없습니다.")
    return memo.model_dump()


@mcp.tool()
@tool_logger(logger, param_keys=["category"])
async def basic_list_memos(category: Optional[str] = None) -> dict[str, Any]:
    """메모 목록을 조회합니다.

    Args:
        category: 필터링 카테고리 — 생략하면 전체 반환

    Returns:
        { total: int, memos: [...] }
    """
    memos = list(_store.values())
    if category:
        memos = [m for m in memos if m.category == category]

    # 포인트 ⑤: 복합 응답은 전용 Response 모델 사용
    return MemoListResponse(total=len(memos), memos=memos).model_dump()


@mcp.tool()
@tool_logger(logger, param_keys=["memo_id"])
async def basic_update_memo(
    memo_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None,
) -> dict[str, Any]:
    """메모를 부분 수정합니다 — 전달한 필드만 변경됩니다.

    Args:
        memo_id: 수정할 메모 ID
        title: 새 제목 (생략하면 기존 값 유지)
        content: 새 본문 (생략하면 기존 값 유지)
        category: 새 카테고리 (생략하면 기존 값 유지)
    """
    memo = _store.get(memo_id)
    if memo is None:
        raise ToolError(f"메모 ID {memo_id}를 찾을 수 없습니다.")

    # 포인트 ⑥: Pydantic model_copy — 불변 객체처럼 업데이트
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
    """메모를 삭제합니다.

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
    """카테고리별 메모 통계를 반환합니다."""
    categories: dict[str, int] = {}
    for memo in _store.values():
        categories[memo.category] = categories.get(memo.category, 0) + 1

    return MemoStatsResponse(total=len(_store), categories=categories).model_dump()
