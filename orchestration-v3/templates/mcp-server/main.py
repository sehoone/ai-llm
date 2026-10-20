#!/usr/bin/env python3
"""MCP 서버 템플릿 CLI.

HTTP transport면 uvicorn("src.asgi:app"), stdio면 mcp.run.
개발 중 hot-reload는 `uv run poe dev`(uvicorn --reload)를 권장.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.logging import get_logger  # noqa: E402 — sys.path 설정 후 import

_logger = get_logger("main")

_USAGE = """\
MCP 서버 템플릿

사용법:
    python main.py server    # MCP 서버 실행 (sample 도메인 도구)
"""


def cmd_server() -> None:
    from src.core.config import settings

    _logger.info(
        "server_starting",
        extra={
            "transport": settings.mcp_transport,
            "host": settings.mcp_host,
            "port": settings.mcp_port,
            "workers": settings.mcp_workers,
        },
    )

    if settings.mcp_transport in ("streamable-http", "http", "sse"):
        import uvicorn

        uvicorn.run(
            "src.asgi:app",
            host=settings.mcp_host,
            port=settings.mcp_port,
            workers=settings.mcp_workers,
            access_log=(settings.log_level == "DEBUG"),
            log_level=settings.log_level.lower(),
            timeout_keep_alive=30,
        )
    else:
        from src.app import mcp
        mcp.run(transport=settings.mcp_transport)


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("help", "--help", "-h"):
        print(_USAGE)
        return

    if args[0] == "server":
        try:
            cmd_server()
        except KeyboardInterrupt:
            print("\n종료합니다.")
    else:
        print(f"알 수 없는 명령어: {args[0]}")
        print(_USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
