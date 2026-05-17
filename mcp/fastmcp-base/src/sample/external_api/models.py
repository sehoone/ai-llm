"""
[케이스 02 - external_api] 환율 조회 모델
"""
from typing import Optional

from pydantic import BaseModel


class ExchangeRate(BaseModel):
    from_currency: str
    to_currency: str
    rate: float
    is_demo: bool = False


class ConvertResult(BaseModel):
    from_currency: str
    to_currency: str
    amount: float
    converted: float
    rate: float
    is_demo: bool = False


class CurrencyInfo(BaseModel):
    code: str
    name: str


class CurrencyListResponse(BaseModel):
    total: int
    currencies: list[CurrencyInfo]
    is_demo: bool = False
