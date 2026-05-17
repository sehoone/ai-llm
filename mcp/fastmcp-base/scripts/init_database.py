#!/usr/bin/env python3
"""데이터베이스 연결 확인 스크립트.

테이블 생성은 scripts/schema.sql 을 직접 실행하세요:
    psql -U postgres -d fastmcp_db -f scripts/schema.sql
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_settings
from src.database.session import create_async_engine_from_settings, test_connection


async def _main() -> None:
    engine = create_async_engine_from_settings(get_settings())
    try:
        ok = await test_connection(engine)
        if ok:
            print("데이터베이스 연결 성공")
        else:
            print("연결 실패 — DATABASE_URL 환경변수를 확인하세요.")
            sys.exit(1)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
