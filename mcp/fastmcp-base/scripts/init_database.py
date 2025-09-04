#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
Alembic 마이그레이션을 초기화하고 테이블을 생성합니다.
"""

import os
import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database_config import get_database_url, engine, Base
from src.database_mcp_server import User, Post
from sqlalchemy import text


async def init_database():
    """데이터베이스 연결 테스트"""
    try:
        print("데이터베이스 연결 테스트 중...")
        
        # 데이터베이스 URL 확인
        db_url = get_database_url()
        print(f"데이터베이스 URL: {db_url}")
        
        # 데이터베이스 연결 테스트
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("데이터베이스 연결 테스트 성공")
            
            # 기존 테이블 확인
            tables_result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = tables_result.fetchall()
            
            if tables:
                print(f"\n기존 테이블 발견 ({len(tables)}개):")
                for table in tables:
                    print(f"- {table[0]}")
            else:
                print("\n기존 테이블이 없습니다.")
                print("필요한 테이블을 직접 생성하거나 다른 도구를 사용하세요.")
        
        print("데이터베이스 연결 테스트가 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print(f"데이터베이스 연결 테스트 중 오류 발생: {e}")
        return False
    
    return True


async def create_sample_data():
    """샘플 데이터 생성 (원시 SQL 사용)"""
    try:
        print("\n샘플 데이터 생성 중...")
        
        async with engine.begin() as conn:
            # 기존 데이터 확인
            user_count = await conn.execute(text("SELECT COUNT(*) FROM users"))
            existing_users = user_count.scalar()
            
            if existing_users > 0:
                print(f"이미 {existing_users}명의 사용자가 존재합니다.")
                response = input("기존 데이터를 유지하고 추가 데이터를 생성하시겠습니까? (y/n): ")
                if response.lower() not in ['y', 'yes']:
                    return True
            
            # 샘플 사용자 생성 (SQL INSERT)
            await conn.execute(text("""
                INSERT INTO users (username, email, full_name, is_active, created_at)
                VALUES 
                    ('admin', 'admin@example.com', 'Admin User', true, NOW()),
                    ('user1', 'user1@example.com', 'Test User 1', true, NOW())
                ON CONFLICT (username) DO NOTHING
            """))
            
            # 사용자 ID 조회
            admin_result = await conn.execute(text("SELECT id FROM users WHERE username = 'admin'"))
            admin_id = admin_result.scalar()
            
            user1_result = await conn.execute(text("SELECT id FROM users WHERE username = 'user1'"))
            user1_id = user1_result.scalar()
            
            if admin_id and user1_id:
                # 샘플 게시물 생성 (SQL INSERT)
                await conn.execute(text("""
                    INSERT INTO posts (title, content, is_published, author_id, created_at, updated_at)
                    VALUES 
                        (:title1, :content1, true, :admin_id, NOW(), NOW()),
                        (:title2, :content2, true, :admin_id, NOW(), NOW()),
                        (:title3, :content3, false, :user1_id, NOW(), NOW())
                """), {
                    "title1": "Welcome to FastMCP",
                    "content1": "This is a sample post created by the database MCP server.",
                    "title2": "Database Integration",
                    "content2": "Successfully integrated PostgreSQL with SQLAlchemy!",
                    "title3": "Hello World",
                    "content3": "My first post!",
                    "admin_id": admin_id,
                    "user1_id": user1_id
                })
        
        print("샘플 데이터 생성 완료!")
        print("- 사용자 2명 (admin, user1)")
        print("- 게시물 3개")
        
    except Exception as e:
        print(f"샘플 데이터 생성 중 오류 발생: {e}")
        return False
    
    return True


async def main():
    """메인 함수"""
    print("=" * 50)
    print("FastMCP 데이터베이스 연결 테스트")
    print("=" * 50)
    
    # 환경변수 확인
    if not get_database_url():
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        print("   .env 파일에 DATABASE_URL을 설정해주세요.")
        print("   예: DATABASE_URL=postgresql://postgres:password@localhost:5432/fastmcp_db")
        return
    
    # 데이터베이스 연결 테스트
    if await init_database():
        print("✅ 데이터베이스 연결 테스트 성공")
        
        # 샘플 데이터 생성 여부 묻기
        response = input("\n샘플 데이터를 생성하시겠습니까? (y/n): ")
        if response.lower() in ['y', 'yes']:
            if await create_sample_data():
                print("✅ 샘플 데이터 생성 성공")
            else:
                print("❌ 샘플 데이터 생성 실패")
    else:
        print("❌ 데이터베이스 연결 테스트 실패")
    
    print("\n테스트 완료!")
    print("\n참고:")
    print("- 이 스크립트는 테이블을 자동으로 생성하지 않습니다")
    print("- 필요한 테이블(users, posts)을 미리 생성해주세요")
    print("- 또는 다른 마이그레이션 도구를 사용하세요")


if __name__ == "__main__":
    asyncio.run(main())
