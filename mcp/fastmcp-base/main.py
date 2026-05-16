#!/usr/bin/env python3
"""FastMCP 베이스 프로젝트 CLI"""

import importlib
import sys
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

_SERVERS: dict[str, tuple[str, str]] = {
    "integrated": ("src.integrated.server", "mcp"),
    "weather": ("src.weather.server", "mcp"),
    "news": ("src.news.server", "mcp"),
    "database": ("src.database.server", "mcp"),
}

_USAGE = """\
FastMCP 베이스 프로젝트

사용법:
    python main.py server [integrated|weather|news|database]
    python main.py init database
    python main.py init tables

예제:
    python main.py server integrated    # 통합 서버 (기본값)
    python main.py server database      # 데이터베이스 서버
    python main.py init database        # DB 연결 확인
    python main.py init tables          # 테이블 생성 (users, posts)
"""


def cmd_server(server_type: str = "integrated") -> None:
    if server_type not in _SERVERS:
        print(f"알 수 없는 서버: {server_type}")
        print(f"사용 가능: {', '.join(_SERVERS)}")
        sys.exit(1)

    module_path, attr = _SERVERS[server_type]
    module = importlib.import_module(module_path)
    mcp: FastMCP = getattr(module, attr)

    from src.core.config import get_settings
    settings = get_settings()

    print(
        f"{server_type} MCP 서버를 시작합니다... "
        f"[{settings.mcp_transport}] {settings.mcp_host}:{settings.mcp_port}"
    )

    if settings.mcp_transport in ("streamable-http", "http", "sse"):
        _run_http_server(mcp, settings)
    else:
        mcp.run(transport=settings.mcp_transport)


def _run_http_server(mcp: FastMCP, settings) -> None:
    import uvicorn
    from src.auth.setup import setup_auth

    middleware = setup_auth(mcp, settings)
    app = mcp.http_app(middleware=middleware, transport=settings.mcp_transport)
    uvicorn.run(
        app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        access_log=(settings.log_level == "DEBUG"),
        log_level=settings.log_level.lower(),
        timeout_keep_alive=30,
    )


def cmd_init(target: str = "database") -> None:
    if target == "database":
        from src.database.session import test_connection
        if test_connection():
            print("데이터베이스 연결 성공")
        else:
            print("데이터베이스 연결 실패 — DATABASE_URL 환경변수를 확인하세요.")
            sys.exit(1)

    elif target == "tables":
        from src.database.orm import Base
        from src.database.session import _get_engine
        engine = _get_engine()
        try:
            Base.metadata.create_all(engine)
            print("테이블 생성 완료: users, posts")
        except Exception as e:
            print(f"테이블 생성 실패: {e}")
            sys.exit(1)

    else:
        print(f"알 수 없는 초기화 대상: {target}")
        print("사용 가능: database, tables")
        sys.exit(1)


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("help", "--help", "-h"):
        print(_USAGE)
        return

    command = args[0]
    sub: Optional[str] = args[1] if len(args) > 1 else None

    try:
        if command == "server":
            cmd_server(sub or "integrated")
        elif command == "init":
            cmd_init(sub or "database")
        else:
            print(f"알 수 없는 명령어: {command}")
            print(_USAGE)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n종료합니다.")


if __name__ == "__main__":
    main()
