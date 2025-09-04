#!/usr/bin/env python3
"""
FastMCP 프로젝트 메인 실행 파일

이 스크립트는 프로젝트의 주요 기능들을 실행할 수 있는 통합 인터페이스를 제공합니다.
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_usage():
    """사용법 출력"""
    print("""
FastMCP 프로젝트 실행기

사용법:
    python main.py <command> [options]

명령어:
    server [integrated|weather|news|database]  - MCP 서버 실행
    test [simple|tools|database|interactive]   - 테스트 실행
    init [database]                             - 초기화 실행
    demo [client|sql]                           - 데모 실행
    help                                        - 도움말 표시

예제:
    python main.py server integrated   # 통합 서버 실행
    python main.py server database     # 데이터베이스 서버 실행
    python main.py test simple         # 간단한 테스트 실행
    python main.py test database       # 데이터베이스 테스트 실행
    python main.py init database       # 데이터베이스 초기화
    python main.py demo client         # 클라이언트 데모 실행
    python main.py demo sql             # SQL 쿼리 데모 실행
""")


async def run_server(server_type="integrated"):
    """MCP 서버 실행"""
    if server_type == "integrated":
        from src.integrated_server import mcp
        print("통합 MCP 서버를 시작합니다...")
        mcp.run()
    elif server_type == "weather":
        from src.weather_mcp_server import mcp
        print("날씨 MCP 서버를 시작합니다...")
        mcp.run()
    elif server_type == "news":
        from src.news_mcp_server import mcp
        print("뉴스 MCP 서버를 시작합니다...")
        mcp.run()
    elif server_type == "database":
        from src.database_mcp_server import mcp
        print("데이터베이스 MCP 서버를 시작합니다...")
        mcp.run()
    else:
        print(f"알 수 없는 서버 타입: {server_type}")
        print("사용 가능한 서버: integrated, weather, news, database")


async def run_test(test_type="simple"):
    """테스트 실행"""
    if test_type == "simple":
        from tests.simple_test import main
        await main()
    elif test_type == "tools":
        from tests.test_tools import main
        await main()
    elif test_type == "database":
        from tests.test_database import main
        await main()
    elif test_type == "interactive":
        from tests.test_tools import interactive_test
        await interactive_test()
    else:
        print(f"알 수 없는 테스트 타입: {test_type}")
        print("사용 가능한 테스트: simple, tools, database, interactive")


async def run_init(init_type="database"):
    """초기화 실행"""
    if init_type == "database":
        from scripts.init_database import main
        await main()
    else:
        print(f"알 수 없는 초기화 타입: {init_type}")
        print("사용 가능한 초기화: database")


async def run_demo(demo_type="client"):
    """데모 실행"""
    if demo_type == "client":
        from examples.client_demo import main
        await main()
    elif demo_type == "sql":
        from examples.sql_query_demo import main
        await main()
    else:
        print(f"알 수 없는 데모 타입: {demo_type}")
        print("사용 가능한 데모: client, sql")


async def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1].lower()

    try:
        if command == "server":
            server_type = sys.argv[2] if len(sys.argv) > 2 else "integrated"
            await run_server(server_type)
        elif command == "test":
            test_type = sys.argv[2] if len(sys.argv) > 2 else "simple"
            await run_test(test_type)
        elif command == "init":
            init_type = sys.argv[2] if len(sys.argv) > 2 else "database"
            await run_init(init_type)
        elif command == "demo":
            demo_type = sys.argv[2] if len(sys.argv) > 2 else "client"
            await run_demo(demo_type)
        elif command == "help":
            print_usage()
        else:
            print(f"알 수 없는 명령어: {command}")
            print_usage()
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())
