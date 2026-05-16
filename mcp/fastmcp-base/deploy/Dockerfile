FROM python:3.13-slim

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/
COPY main.py ./

ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    LOG_LEVEL=INFO \
    SERVER_TYPE=integrated

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD uv run python main.py server "$SERVER_TYPE"
