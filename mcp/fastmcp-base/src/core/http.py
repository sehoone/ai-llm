import asyncio
from typing import Optional

import httpx

from src.core.config import Settings


def create_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.http_timeout)


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_retries: int = 3,
    **kwargs,
) -> httpx.Response:
    """지수 백오프 재시도. 5xx·연결 오류만 재시도, 4xx는 즉시 반환."""
    last_error: Optional[Exception] = RuntimeError("max_retries must be >= 0")
    for attempt in range(max(0, max_retries) + 1):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code < 500:
                return response
            last_error = httpx.HTTPStatusError(
                f"Server error {response.status_code}",
                request=response.request,
                response=response,
            )
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = e
        if attempt < max_retries:
            await asyncio.sleep(2**attempt)
    raise last_error  # type: ignore[misc]
