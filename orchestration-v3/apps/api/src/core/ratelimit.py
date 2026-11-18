"""경량 인메모리 레이트리밋 (ADR-0020 — 셀프 가입 남용 완화).

고정 윈도우 카운터를 IP별로 센다. **단일 프로세스 한정** — 멀티 레플리카/수평 확장 시에는
공유 저장소(Redis 등) 기반으로 교체해야 한다. 지금은 공개 셀프 가입의 기본 남용 방지 수준.

사용:
    from src.core.ratelimit import rate_limit
    @router.post("/register", dependencies=[Depends(rate_limit(5, 300))])  # IP당 5분에 5회
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import HTTPException, Request

# 서로 다른 IP가 쌓여 무한정 커지는 것을 막는 상한(초과 시 만료 항목 정리).
_MAX_KEYS = 10_000


class _FixedWindow:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, tuple[int, float]] = {}

    def check(self, key: str) -> None:
        now = time.monotonic()
        count, start = self._hits.get(key, (0, now))
        if now - start >= self.window:  # 윈도우 경과 → 리셋
            count, start = 0, now
        count += 1
        self._hits[key] = (count, start)
        if len(self._hits) > _MAX_KEYS:
            self._prune(now)
        if count > self.limit:
            retry = max(1, int(self.window - (now - start)))
            raise HTTPException(
                status_code=429,
                detail=f"요청이 너무 많습니다. {retry}초 후 다시 시도하세요.",
                headers={"Retry-After": str(retry)},
            )

    def _prune(self, now: float) -> None:
        expired = [k for k, (_, start) in self._hits.items() if now - start >= self.window]
        for k in expired:
            del self._hits[k]


def _client_ip(request: Request) -> str:
    # nginx 뒤 — X-Forwarded-For의 첫 주소를 신뢰(단일 신뢰 프록시 전제).
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(limit: int, window_seconds: int) -> Callable[[Request], None]:
    """IP당 (limit회 / window_seconds초)를 초과하면 429. 반환값을 Depends로 주입한다.

    팩토리는 라우트 정의 시 1회 호출되어 limiter 인스턴스를 만든다 — 상태가 프로세스 수명 동안 유지된다.
    """
    limiter = _FixedWindow(limit, window_seconds)

    def dependency(request: Request) -> None:
        limiter.check(_client_ip(request))

    return dependency
