"""
[케이스 01 - basic] Pydantic 모델 정의

핵심 패턴:
  - BaseModel 상속으로 입출력 타입 명시
  - tool은 model.model_dump() 로 dict 반환
  - Optional 필드는 None 기본값 사용
"""
from typing import Optional

from pydantic import BaseModel


class Memo(BaseModel):
    id: int
    title: str
    content: str
    category: str
    created_at: str
    updated_at: str


class MemoListResponse(BaseModel):
    total: int
    memos: list[Memo]


class MemoStatsResponse(BaseModel):
    total: int
    categories: dict[str, int]  # { category명: 메모 수 }
