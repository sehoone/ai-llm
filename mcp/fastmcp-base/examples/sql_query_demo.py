#!/usr/bin/env python3
"""
Database SQL 쿼리 예제 스크립트
원시 SQL 쿼리와 분석 쿼리를 실행하는 예제를 보여줍니다.
"""

import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def demo_raw_queries():
    """원시 SQL 쿼리 데모"""
    try:
        from src.database_mcp_server import (
            execute_raw_query, get_table_schema, 
            list_tables, execute_analytics_query
        )
        
        print("🔍 원시 SQL 쿼리 예제")
        print("=" * 50)
        
        # 1. 테이블 목록 조회
        print("\n1. 데이터베이스 테이블 목록 조회")
        print("쿼리: SELECT table_name FROM information_schema.tables")
        result = await list_tables()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 2. 테이블 스키마 조회
        print("\n2. users 테이블 스키마 조회")
        result = await get_table_schema("users")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 3. 간단한 COUNT 쿼리
        print("\n3. 사용자 수 조회")
        print("쿼리: SELECT COUNT(*) as total_users FROM users")
        result = await execute_raw_query("SELECT COUNT(*) as total_users FROM users")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 4. JOIN 쿼리
        print("\n4. 사용자별 게시물 수 조회 (JOIN)")
        query = """
            SELECT 
                u.username,
                u.email,
                COUNT(p.id) as post_count
            FROM users u
            LEFT JOIN posts p ON u.id = p.user_id
            GROUP BY u.id, u.username, u.email
            ORDER BY post_count DESC
        """
        print(f"쿼리: {query}")
        result = await execute_raw_query(query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 5. 복잡한 분석 쿼리
        print("\n5. 게시물 작성 동향 (최근 30일)")
        query = """
            SELECT 
                DATE(created_at) as post_date,
                COUNT(*) as posts_count,
                COUNT(DISTINCT user_id) as active_users,
                AVG(LENGTH(content)) as avg_content_length
            FROM posts
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY post_date DESC
            LIMIT 10
        """
        print(f"쿼리: {query}")
        result = await execute_raw_query(query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except ImportError as e:
        print(f"❌ 모듈 import 오류: {e}")
        print("데이터베이스 서버가 설정되지 않았습니다.")
    except Exception as e:
        print(f"❌ 쿼리 실행 오류: {e}")


async def demo_analytics_queries():
    """분석 쿼리 데모"""
    try:
        from src.database_mcp_server import execute_analytics_query
        
        print("\n\n📈 분석 쿼리 예제")
        print("=" * 50)
        
        # 1. 사용자 활동 분석
        print("\n1. 사용자 활동 분석")
        result = await execute_analytics_query("user_activity")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 2. 인기 사용자 조회
        print("\n2. 인기 사용자 TOP 5")
        result = await execute_analytics_query("popular_users", {"limit": 5})
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 3. 최근 활동 조회
        print("\n3. 최근 활동 TOP 10")
        result = await execute_analytics_query("recent_activity", {"limit": 10})
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 4. 게시물 트렌드 분석
        print("\n4. 게시물 트렌드 (최근 30일)")
        result = await execute_analytics_query("post_trends")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ 분석 쿼리 실행 오류: {e}")


async def demo_parameterized_queries():
    """매개변수가 있는 쿼리 데모"""
    try:
        from src.database_mcp_server import execute_raw_query
        
        print("\n\n🎯 매개변수 쿼리 예제")
        print("=" * 50)
        
        # 1. 특정 사용자의 게시물 조회
        print("\n1. 특정 사용자의 게시물 조회")
        query = """
            SELECT 
                p.title,
                p.content,
                p.created_at,
                u.username
            FROM posts p
            INNER JOIN users u ON p.user_id = u.id
            WHERE u.username = :username
            ORDER BY p.created_at DESC
        """
        params = {"username": "admin"}  # 매개변수
        print(f"쿼리: {query}")
        print(f"매개변수: {params}")
        result = await execute_raw_query(query, params)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 2. 날짜 범위로 게시물 검색
        print("\n2. 특정 날짜 이후 게시물 조회")
        query = """
            SELECT 
                title,
                created_at,
                CASE 
                    WHEN LENGTH(content) > 50 
                    THEN SUBSTRING(content, 1, 50) || '...'
                    ELSE content
                END as content_preview
            FROM posts
            WHERE created_at >= :start_date
            ORDER BY created_at DESC
            LIMIT :limit
        """
        params = {
            "start_date": "2024-01-01",
            "limit": 5
        }
        print(f"쿼리: {query}")
        print(f"매개변수: {params}")
        result = await execute_raw_query(query, params)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ 매개변수 쿼리 실행 오류: {e}")


async def main():
    """메인 함수"""
    print("FastMCP Database SQL 쿼리 예제")
    print("=" * 60)
    
    # 환경변수 확인
    import os
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        print("데모 쿼리를 실행하지만 실제 데이터베이스에 연결되지 않습니다.")
        print("실제 데이터베이스 연결을 위해 .env 파일에 DATABASE_URL을 설정하세요.")
        print()
    
    # 각 예제 실행
    await demo_raw_queries()
    await demo_analytics_queries()
    await demo_parameterized_queries()
    
    print("\n\n🎉 SQL 쿼리 예제 완료!")
    print("\n다음 단계:")
    print("1. PostgreSQL 설치 및 설정")
    print("2. .env 파일에 DATABASE_URL 설정")
    print("3. 데이터베이스 초기화: uv run python main.py init database")
    print("4. 데이터베이스 서버 실행: uv run python main.py server database")
    print("5. 실제 데이터로 쿼리 테스트: uv run python main.py test database")


if __name__ == "__main__":
    asyncio.run(main())
