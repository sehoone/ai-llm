#!/usr/bin/env python3
"""데이터베이스 초기화 스크립트 — 연결 확인 및 테이블 생성."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from src.database.orm import Base
from src.database.session import _get_engine, get_session, test_connection


def check_connection() -> bool:
    print("데이터베이스 연결 테스트 중...")
    if test_connection():
        print("연결 성공")
        return True
    print("연결 실패 — DATABASE_URL 환경변수를 확인하세요.")
    return False


def create_tables() -> None:
    print("테이블 생성 중...")
    engine = _get_engine()
    Base.metadata.create_all(engine)
    print("완료: users, posts")


def show_existing_tables() -> None:
    with get_session() as db:
        result = db.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        )
        tables = [row[0] for row in result]
    if tables:
        print(f"현재 테이블 ({len(tables)}개): {', '.join(tables)}")
    else:
        print("테이블 없음")


def main() -> None:
    if not check_connection():
        sys.exit(1)

    show_existing_tables()

    answer = input("\n테이블을 생성(또는 재확인)하시겠습니까? (y/n): ").strip().lower()
    if answer in ("y", "yes"):
        create_tables()
        show_existing_tables()
    else:
        print("건너뜁니다.")


if __name__ == "__main__":
    main()
