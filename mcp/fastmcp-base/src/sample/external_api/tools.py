"""
[케이스 02 - external_api] 외부 HTTP API 호출 패턴

다루는 패턴:
  1. httpx.AsyncClient — 비동기 HTTP 요청
  2. demo mode — API 키 미설정 시 고정 데이터 반환
  3. HTTPStatusError 처리 — 상태 코드별 분기
  4. 타임아웃·예외 처리 체인
  5. 파라미터 가공 (쿼리스트링 조립)
  6. is_demo 플래그로 응답 구분

app.py 등록:
    from src.sample.external_api import tools as ext_api_tools  # noqa: F401

실제 API: https://api.frankfurter.app (무료, 키 불필요)
데모 모드: settings.exchange_api_key == "demo_key" 일 때
"""
from typing import Any, Optional

import httpx
from fastmcp.exceptions import ToolError

from src.core.config import get_settings
from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp
from src.sample.external_api.models import (
    ConvertResult,
    CurrencyInfo,
    CurrencyListResponse,
    ExchangeRate,
)

logger = get_logger("sample.external_api")

# ── 데모 데이터 ───────────────────────────────────────────────────────────────
_DEMO_RATES: dict[str, float] = {
    "USD": 1350.0, "EUR": 1470.0, "JPY": 9.1,
    "GBP": 1710.0, "CNY": 186.0, "AUD": 880.0,
}
_DEMO_CURRENCIES = [
    CurrencyInfo(code="KRW", name="Korean Won"),
    CurrencyInfo(code="USD", name="US Dollar"),
    CurrencyInfo(code="EUR", name="Euro"),
    CurrencyInfo(code="JPY", name="Japanese Yen"),
    CurrencyInfo(code="GBP", name="British Pound"),
    CurrencyInfo(code="CNY", name="Chinese Yuan"),
    CurrencyInfo(code="AUD", name="Australian Dollar"),
]

# 실제 프로젝트에서는 Settings 클래스에 exchange_api_key 필드 추가
# 여기서는 Settings에 없는 값이므로 환경변수에서 직접 읽거나 하드코딩 처리
_EXCHANGE_BASE_URL = "https://api.frankfurter.app"


def _is_demo() -> bool:
    """API 키가 없으면 데모 모드로 동작"""
    import os
    return os.getenv("EXCHANGE_API_KEY", "demo_key") in ("demo_key", "")


# ── Tool 1: 환율 조회 ─────────────────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=["from_currency", "to_currency"])
async def get_exchange_rate(from_currency: str, to_currency: str) -> dict[str, Any]:
    """두 통화 간 현재 환율을 조회합니다.

    Args:
        from_currency: 기준 통화 코드 (예: USD, EUR, KRW)
        to_currency: 대상 통화 코드 (예: KRW, JPY, USD)

    Returns:
        { from_currency, to_currency, rate, is_demo }
    """
    from_currency = from_currency.upper().strip()
    to_currency = to_currency.upper().strip()

    if from_currency == to_currency:
        raise ToolError("기준 통화와 대상 통화가 같습니다.")

    # 포인트 ①: 데모 모드 분기 — API 키 없어도 동작
    if _is_demo():
        if from_currency == "KRW":
            rate = round(1.0 / _DEMO_RATES.get(to_currency, 0), 6)
            if rate == 0:
                raise ToolError(f"지원하지 않는 통화 코드: {to_currency}")
        else:
            base_rate = _DEMO_RATES.get(from_currency)
            if base_rate is None:
                raise ToolError(f"지원하지 않는 통화 코드: {from_currency}")
            if to_currency == "KRW":
                rate = base_rate
            else:
                to_rate = _DEMO_RATES.get(to_currency)
                if to_rate is None:
                    raise ToolError(f"지원하지 않는 통화 코드: {to_currency}")
                rate = round(base_rate / to_rate, 6)

        return ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            is_demo=True,
        ).model_dump()

    # 포인트 ②: httpx.AsyncClient — async with 패턴으로 자원 해제 보장
    try:
        async with httpx.AsyncClient(timeout=get_settings().http_timeout) as client:
            response = await client.get(
                f"{_EXCHANGE_BASE_URL}/latest",
                params={"from": from_currency, "to": to_currency},
            )
            # 포인트 ③: raise_for_status() → HTTPStatusError 발생
            response.raise_for_status()
            data = response.json()

        rate = data["rates"].get(to_currency)
        if rate is None:
            raise ToolError(f"환율 데이터를 가져올 수 없습니다: {to_currency}")

        return ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
        ).model_dump()

    # 포인트 ④: 예외 처리 체인 — 구체적 예외 먼저, 범용 예외 마지막
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ToolError(f"지원하지 않는 통화 코드입니다: {from_currency} → {to_currency}")
        raise ToolError(f"API 오류: HTTP {e.response.status_code}")
    except httpx.TimeoutException:
        raise ToolError("환율 API 응답 시간 초과")
    except ToolError:
        raise  # ToolError는 재발생 (로그 중복 방지)
    except Exception as e:
        logger.exception("get_exchange_rate failed", **{"from": from_currency, "to": to_currency})
        raise ToolError(f"예상치 못한 오류: {e}")


# ── Tool 2: 금액 환산 ─────────────────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=["from_currency", "to_currency", "amount"])
async def convert_currency(
    from_currency: str,
    to_currency: str,
    amount: float,
) -> dict[str, Any]:
    """금액을 다른 통화로 환산합니다.

    Args:
        from_currency: 원본 통화 코드 (예: USD)
        to_currency: 환산 통화 코드 (예: KRW)
        amount: 환산할 금액 (양수)

    Returns:
        { from_currency, to_currency, amount, converted, rate, is_demo }
    """
    if amount <= 0:
        raise ToolError("금액은 0보다 커야 합니다.")

    # 포인트 ⑤: 기존 tool을 재사용 — DRY 원칙
    rate_result = await get_exchange_rate(from_currency, to_currency)
    rate = rate_result["rate"]
    converted = round(amount * rate, 2)

    return ConvertResult(
        from_currency=rate_result["from_currency"],
        to_currency=rate_result["to_currency"],
        amount=amount,
        converted=converted,
        rate=rate,
        is_demo=rate_result["is_demo"],
    ).model_dump()


# ── Tool 3: 지원 통화 목록 ────────────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=[])
async def get_supported_currencies() -> dict[str, Any]:
    """지원하는 통화 코드 목록을 반환합니다."""
    if _is_demo():
        return CurrencyListResponse(
            total=len(_DEMO_CURRENCIES),
            currencies=_DEMO_CURRENCIES,
            is_demo=True,
        ).model_dump()

    try:
        async with httpx.AsyncClient(timeout=get_settings().http_timeout) as client:
            response = await client.get(f"{_EXCHANGE_BASE_URL}/currencies")
            response.raise_for_status()
            data = response.json()  # { "AUD": "Australian Dollar", ... }

        currencies = [CurrencyInfo(code=code, name=name) for code, name in data.items()]
        return CurrencyListResponse(total=len(currencies), currencies=currencies).model_dump()

    except httpx.HTTPStatusError as e:
        raise ToolError(f"API 오류: HTTP {e.response.status_code}")
    except Exception as e:
        logger.exception("get_supported_currencies failed")
        raise ToolError(str(e))
