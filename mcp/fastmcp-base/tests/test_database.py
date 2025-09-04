"""
Database MCP Server 테스트
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_database_functions():
    """데이터베이스 기능 테스트"""
    print("=== Database MCP Server 기능 테스트 ===")
    
    try:
        # 데이터베이스 서버에서 함수 import
        from src.database_mcp_server import (
            get_database_stats, create_user, get_users, 
            create_post, get_posts, search_posts,
            init_database, execute_raw_query, get_table_schema,
            list_tables, execute_analytics_query
        )
        
        # 1. 데이터베이스 초기화 테스트
        print("\n1. 데이터베이스 연결 테스트")
        if init_database():
            print("✓ 데이터베이스 연결 성공")
        else:
            print("✗ 데이터베이스 연결 실패 - 데모 데이터로 진행")
            await test_demo_data()
            return
        
        # 2. 데이터베이스 통계
        print("\n2. 데이터베이스 통계 조회")
        stats = await get_database_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        # 3. 사용자 생성 테스트
        print("\n3. 사용자 생성 테스트")
        user_result = await create_user(
            username="testuser",
            email="test@example.com",
            full_name="테스트 사용자"
        )
        print(json.dumps(user_result, indent=2, ensure_ascii=False))
        
        if user_result.get("success"):
            user_id = user_result["user"]["id"]
            
            # 4. 게시글 생성 테스트
            print("\n4. 게시글 생성 테스트")
            post_result = await create_post(
                title="FastMCP 데이터베이스 연동 테스트",
                content="SQLAlchemy와 PostgreSQL을 사용한 MCP 서버 테스트입니다.",
                author_id=user_id,
                is_published=True
            )
            print(json.dumps(post_result, indent=2, ensure_ascii=False))
        
        # 5. 사용자 목록 조회
        print("\n5. 사용자 목록 조회")
        users = await get_users(limit=5)
        print(json.dumps(users, indent=2, ensure_ascii=False))
        
        # 6. 게시글 목록 조회
        print("\n6. 게시글 목록 조회")
        posts = await get_posts(limit=5, published_only=True)
        print(json.dumps(posts, indent=2, ensure_ascii=False))
        
        # 7. 게시글 검색 테스트
        print("\n7. 게시글 검색 테스트")
        search_result = await search_posts("FastMCP", limit=3)
        print(json.dumps(search_result, indent=2, ensure_ascii=False))
        
        # 8. 최종 통계
        print("\n8. 업데이트된 데이터베이스 통계")
        final_stats = await get_database_stats()
        print(json.dumps(final_stats, indent=2, ensure_ascii=False))
        
        # 9. 원시 SQL 쿼리 테스트
        print("\n9. 원시 SQL 쿼리 테스트")
        await test_raw_sql_queries()
        
    except ImportError as e:
        print(f"Import 오류: {e}")
        await test_demo_data()
    except Exception as e:
        print(f"테스트 실행 오류: {e}")
        await test_demo_data()


async def test_raw_sql_queries():
    """원시 SQL 쿼리 도구들 테스트"""
    try:
        from src.database_mcp_server import (
            execute_raw_query, get_table_schema,
            list_tables, execute_analytics_query
        )
        
        print("🔍 원시 SQL 쿼리 도구 테스트")
        print("-" * 30)
        
        # 테이블 목록 조회
        print("📋 테이블 목록 조회")
        result = await list_tables()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # 테이블 스키마 조회
        print("🏗️ users 테이블 스키마 조회")
        result = await get_table_schema("users")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        print("🏗️ posts 테이블 스키마 조회")
        result = await get_table_schema("posts")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # 원시 SQL 쿼리 실행 (SELECT)
        print("📝 원시 SQL 쿼리 실행 - 사용자 수 조회")
        result = await execute_raw_query("SELECT COUNT(*) as total_users FROM users")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        print("📝 원시 SQL 쿼리 실행 - 게시물 수 조회")
        result = await execute_raw_query("SELECT COUNT(*) as total_posts FROM posts")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        print("📝 원시 SQL 쿼리 실행 - 사용자별 게시물 수")
        query = """
            SELECT u.username, COUNT(p.id) as post_count
            FROM users u
            LEFT JOIN posts p ON u.id = p.user_id
            GROUP BY u.id, u.username
            ORDER BY post_count DESC
        """
        result = await execute_raw_query(query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # 분석 쿼리 실행
        print("📈 분석 쿼리 실행 - 사용자 활동")
        result = await execute_analytics_query("user_activity")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        print("📈 분석 쿼리 실행 - 최근 활동 (3개)")
        result = await execute_analytics_query("recent_activity", {"limit": 3})
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        print("📈 분석 쿼리 실행 - 인기 사용자 (5명)")
        result = await execute_analytics_query("popular_users", {"limit": 5})
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
    except Exception as e:
        print(f"원시 SQL 쿼리 테스트 오류: {e}")


async def test_demo_data():
    """데모 데이터 테스트 (데이터베이스 연결이 안 될 때)"""
    print("\n=== 데모 데이터 테스트 ===")
    
    # 가상의 데이터베이스 응답 시뮬레이션
    demo_stats = {
        "statistics": {
            "total_users": 5,
            "active_users": 4,
            "total_posts": 12,
            "published_posts": 8,
            "draft_posts": 4
        },
        "recent_activity": {
            "recent_users": [
                {"id": 1, "username": "admin", "created_at": "2024-01-01T10:00:00"},
                {"id": 2, "username": "testuser", "created_at": "2024-01-02T11:30:00"}
            ],
            "recent_posts": [
                {"id": 1, "title": "첫 번째 게시글", "author": "admin", "created_at": "2024-01-01T12:00:00"},
                {"id": 2, "title": "FastMCP 소개", "author": "testuser", "created_at": "2024-01-02T14:00:00"}
            ]
        }
    }
    
    demo_users = {
        "users": [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "full_name": "관리자",
                "is_active": True,
                "created_at": "2024-01-01T10:00:00",
                "post_count": 5
            },
            {
                "id": 2,
                "username": "testuser",
                "email": "test@example.com",
                "full_name": "테스트 사용자",
                "is_active": True,
                "created_at": "2024-01-02T11:30:00",
                "post_count": 3
            }
        ],
        "total_count": 2,
        "limit": 10,
        "offset": 0
    }
    
    demo_posts = {
        "posts": [
            {
                "id": 1,
                "title": "FastMCP와 SQLAlchemy 연동",
                "content": "FastMCP를 사용하여 데이터베이스와 연동하는 방법을 알아봅니다...",
                "is_published": True,
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00",
                "author": {
                    "id": 1,
                    "username": "admin",
                    "full_name": "관리자"
                }
            },
            {
                "id": 2,
                "title": "PostgreSQL 설정 가이드",
                "content": "PostgreSQL 데이터베이스를 설정하고 연결하는 방법을 설명합니다...",
                "is_published": True,
                "created_at": "2024-01-02T14:00:00",
                "updated_at": "2024-01-02T14:00:00",
                "author": {
                    "id": 2,
                    "username": "testuser",
                    "full_name": "테스트 사용자"
                }
            }
        ],
        "total_count": 2,
        "limit": 10,
        "offset": 0,
        "published_only": True
    }
    
    print("\n1. 데이터베이스 통계 (데모)")
    print(json.dumps(demo_stats, indent=2, ensure_ascii=False))
    
    print("\n2. 사용자 목록 (데모)")
    print(json.dumps(demo_users, indent=2, ensure_ascii=False))
    
    print("\n3. 게시글 목록 (데모)")
    print(json.dumps(demo_posts, indent=2, ensure_ascii=False))
    
    print("\n참고: 실제 데이터베이스 기능을 사용하려면 PostgreSQL을 설치하고")
    print("DATABASE_URL 환경변수를 설정하세요.")
    print("예: DATABASE_URL=postgresql://postgres:password@localhost:5432/fastmcp_db")


async def main():
    """메인 테스트 함수"""
    print("Database MCP Server 테스트 시작")
    print("=" * 50)
    
    await test_database_functions()
    
    print("\n" + "=" * 50)
    print("테스트 완료!")
    print("\n다음 단계:")
    print("1. PostgreSQL 설치 및 설정")
    print("2. DATABASE_URL 환경변수 설정")
    print("3. 데이터베이스 서버 실행: uv run python src/database_mcp_server.py")


if __name__ == "__main__":
    asyncio.run(main())
