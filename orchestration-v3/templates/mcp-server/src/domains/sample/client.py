"""[sample 도메인] 외부 REST/HTTP egress 어댑터.

HTTP 세부사항(헤더·재시도·URL 조립)을 여기에 격리한다. service 계층이 이 클라이언트를 호출한다.
httpx.AsyncClient 는 lifespan 에서 생성한 공유 인스턴스를 주입받아 커넥션을 재사용한다.
"""
from typing import Any

import httpx

from src.core.http import request_with_retry


class SampleApiClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        max_retries: int = 3,
    ) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}

    async def fetch_item(self, item_id: str) -> dict[str, Any]:
        resp = await request_with_retry(
            self._http,
            "GET",
            f"{self._base_url}/items/{item_id}",
            max_retries=self._max_retries,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()
