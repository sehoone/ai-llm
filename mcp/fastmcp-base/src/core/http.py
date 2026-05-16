import asyncio
from typing import Any

import httpx

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger("core.http")


async def fetch_json(
    url: str,
    params: dict[str, Any],
    timeout: float | None = None,
) -> dict[str, Any]:
    """GET 요청 후 JSON 반환. 네트워크 오류 시 지수 백오프로 재시도.

    HTTPStatusError(4xx/5xx)는 재시도하지 않고 즉시 재발생.
    """
    settings = get_settings()
    _timeout = timeout if timeout is not None else settings.http_timeout
    max_retries = settings.http_max_retries

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=_timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            logger.warning(
                f"HTTP request failed (attempt {attempt + 1}/{max_retries}), "
                f"retry in {wait}s: {exc}"
            )
            await asyncio.sleep(wait)

    raise RuntimeError("unreachable")
