"""
[케이스 03 - database] 상품(Product) 관리 Pydantic 모델
"""
from typing import Optional

from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    category: str
    is_active: bool
    created_at: str


class ProductListResponse(BaseModel):
    products: list[ProductResponse]
    total_count: int
    limit: int
    offset: int
