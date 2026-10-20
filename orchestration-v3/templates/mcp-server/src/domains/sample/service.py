"""[sample 도메인] 비즈니스 로직 — 외부 REST(client)와 DB(repository)를 조합.

apps/api의 service 계층에 대응. 도구(tools)는 이 서비스만 호출하고, 외부 egress는 어댑터에 격리.
한 도메인이 여러 외부 시스템(REST + DB)을 조합하는 지점을 보여준다.
"""
import httpx
from fastmcp.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import settings
from src.domains.sample import repository
from src.domains.sample.client import SampleApiClient
from src.domains.sample.models import SampleItem, SampleOverview, SampleRecord

_DEMO_ITEM = SampleItem(id="demo-1", name="데모 아이템", is_demo=True)


class SampleService:
    def __init__(
        self,
        http: httpx.AsyncClient,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._http = http
        self._session_factory = session_factory

    async def get_item(self, item_id: str) -> SampleItem:
        item_id = item_id.strip()
        if not item_id:
            raise ToolError("item_id는 비어 있을 수 없습니다.")

        # API 키가 없으면 외부 호출 없이 데모 데이터 반환
        if settings.is_demo_sample:
            return _DEMO_ITEM.model_copy(update={"id": item_id})

        client = SampleApiClient(
            self._http,
            settings.sample_base_url,
            settings.sample_api_key,
            settings.http_max_retries,
        )
        try:
            raw = await client.fetch_item(item_id)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ToolError(f"아이템을 찾을 수 없습니다: {item_id}")
            raise ToolError(f"외부 시스템 오류 (status={e.response.status_code})")
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise ToolError(f"외부 시스템 연결 실패: {e}")
        return SampleItem(**raw)

    async def list_records(self, limit: int) -> list[SampleRecord]:
        limit = max(1, min(limit, settings.db_max_page_size))
        rows = await repository.find_records(self._session_factory, limit)
        return [SampleRecord.model_validate(r) for r in rows]

    async def get_overview(self, item_id: str) -> SampleOverview:
        """외부 아이템 + 로컬 레코드 수를 조합 (REST + DB 동시 사용 예시)."""
        item = await self.get_item(item_id)
        count = await repository.count_records(self._session_factory)
        return SampleOverview(item=item, local_record_count=count)
