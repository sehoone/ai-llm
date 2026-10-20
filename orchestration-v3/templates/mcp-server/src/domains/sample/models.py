"""[sample 도메인] pydantic 입출력 스키마 (apps/api의 schema 계층에 대응)."""

from pydantic import BaseModel, ConfigDict


class SampleItem(BaseModel):
    """외부 REST 시스템의 아이템."""

    id: str
    name: str
    is_demo: bool = False


class SampleRecord(BaseModel):
    """로컬 DB 레코드."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    value: str | None = None


class SampleOverview(BaseModel):
    """도메인 조합 뷰 — 외부 아이템 + 로컬 레코드 수를 한 번에."""

    item: SampleItem
    local_record_count: int
