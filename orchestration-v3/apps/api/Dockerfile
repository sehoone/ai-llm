FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# uv 바이너리
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 먼저 (레이어 캐시) — uv.lock 필요 (로컬에서 `uv sync`로 생성)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# 비루트 실행 (ADR-0032) — 컨테이너 탈취 시 영향 축소. /app·uploads 소유권을 appuser로.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/uploads \
    && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000
# --proxy-headers + --forwarded-allow-ips: nginx 뒤라 X-Forwarded-* 를 신뢰해 scheme·client IP를 복원.
CMD ["uv", "run", "--no-dev", "uvicorn", "src.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
