"""
Database MCP Server - SQLAlchemy와 PostgreSQL을 사용한 데이터베이스 연동 서버
"""

import asyncio
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastmcp import FastMCP
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
import json


# MCP 서버 초기화
mcp = FastMCP("Database MCP Server")

# 데이터베이스 설정
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/fastmcp_db"
)

# SQLAlchemy 설정
Base = declarative_base()
engine = None
SessionLocal = None



# 데이터베이스 모델 정의
class User(Base):
    """사용자 모델"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    posts = relationship("Post", back_populates="author")


class Post(Base):
    """게시글 모델"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"))
    
    # 관계
    author = relationship("User", back_populates="posts")


def init_database():
    """데이터베이스 연결 초기화 (테이블 생성 없음)"""
    global engine, SessionLocal
    
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # 데이터베이스 연결 테스트만 수행
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        return False


def get_db_session():
    """데이터베이스 세션 획득"""
    if SessionLocal is None:
        if not init_database():
            return None
    
    try:
        return SessionLocal()
    except Exception as e:
        print(f"세션 생성 실패: {e}")
        return None


@mcp.tool()
async def create_user(username: str, email: str, full_name: Optional[str] = None) -> Dict[str, Any]:
    """
    새로운 사용자를 생성합니다.
    
    Args:
        username: 사용자명 (고유값)
        email: 이메일 주소 (고유값)
        full_name: 전체 이름 (선택사항)
    
    Returns:
        생성된 사용자 정보
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        # 중복 확인
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return {"error": "이미 존재하는 사용자명 또는 이메일입니다."}
        
        # 새 사용자 생성
        new_user = User(
            username=username,
            email=email,
            full_name=full_name
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "success": True,
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "is_active": new_user.is_active,
                "created_at": new_user.created_at.isoformat()
            }
        }
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"error": f"데이터베이스 오류: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def get_users(limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """
    사용자 목록을 조회합니다.
    
    Args:
        limit: 조회할 사용자 수 (기본값: 10)
        offset: 건너뛸 사용자 수 (기본값: 0)
    
    Returns:
        사용자 목록
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        users = db.query(User).offset(offset).limit(limit).all()
        total_count = db.query(User).count()
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "post_count": len(user.posts)
            })
        
        return {
            "users": user_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def get_user_by_id(user_id: int) -> Dict[str, Any]:
    """
    ID로 사용자 정보를 조회합니다.
    
    Args:
        user_id: 사용자 ID
    
    Returns:
        사용자 정보
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {"error": f"ID {user_id}인 사용자를 찾을 수 없습니다."}
        
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "posts": [
                    {
                        "id": post.id,
                        "title": post.title,
                        "is_published": post.is_published,
                        "created_at": post.created_at.isoformat()
                    } for post in user.posts
                ]
            }
        }
    
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def create_post(title: str, content: str, author_id: int, is_published: bool = False) -> Dict[str, Any]:
    """
    새로운 게시글을 생성합니다.
    
    Args:
        title: 게시글 제목
        content: 게시글 내용
        author_id: 작성자 ID
        is_published: 발행 여부 (기본값: False)
    
    Returns:
        생성된 게시글 정보
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        # 작성자 존재 확인
        author = db.query(User).filter(User.id == author_id).first()
        if not author:
            return {"error": f"ID {author_id}인 사용자를 찾을 수 없습니다."}
        
        # 새 게시글 생성
        new_post = Post(
            title=title,
            content=content,
            author_id=author_id,
            is_published=is_published
        )
        
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        return {
            "success": True,
            "post": {
                "id": new_post.id,
                "title": new_post.title,
                "content": new_post.content,
                "is_published": new_post.is_published,
                "created_at": new_post.created_at.isoformat(),
                "author": {
                    "id": author.id,
                    "username": author.username,
                    "full_name": author.full_name
                }
            }
        }
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"error": f"데이터베이스 오류: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def get_posts(limit: int = 10, offset: int = 0, published_only: bool = False) -> Dict[str, Any]:
    """
    게시글 목록을 조회합니다.
    
    Args:
        limit: 조회할 게시글 수 (기본값: 10)
        offset: 건너뛸 게시글 수 (기본값: 0)
        published_only: 발행된 게시글만 조회 (기본값: False)
    
    Returns:
        게시글 목록
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        query = db.query(Post)
        
        if published_only:
            query = query.filter(Post.is_published == True)
        
        posts = query.order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
        total_count = query.count()
        
        post_list = []
        for post in posts:
            post_list.append({
                "id": post.id,
                "title": post.title,
                "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
                "is_published": post.is_published,
                "created_at": post.created_at.isoformat(),
                "updated_at": post.updated_at.isoformat(),
                "author": {
                    "id": post.author.id,
                    "username": post.author.username,
                    "full_name": post.author.full_name
                }
            })
        
        return {
            "posts": post_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "published_only": published_only
        }
    
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def update_post(post_id: int, title: Optional[str] = None, content: Optional[str] = None, is_published: Optional[bool] = None) -> Dict[str, Any]:
    """
    게시글을 수정합니다.
    
    Args:
        post_id: 게시글 ID
        title: 새로운 제목 (선택사항)
        content: 새로운 내용 (선택사항)
        is_published: 발행 여부 (선택사항)
    
    Returns:
        수정된 게시글 정보
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            return {"error": f"ID {post_id}인 게시글을 찾을 수 없습니다."}
        
        # 필드 업데이트
        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        if is_published is not None:
            post.is_published = is_published
        
        post.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(post)
        
        return {
            "success": True,
            "post": {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "is_published": post.is_published,
                "created_at": post.created_at.isoformat(),
                "updated_at": post.updated_at.isoformat(),
                "author": {
                    "id": post.author.id,
                    "username": post.author.username,
                    "full_name": post.author.full_name
                }
            }
        }
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"error": f"데이터베이스 오류: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def delete_post(post_id: int) -> Dict[str, Any]:
    """
    게시글을 삭제합니다.
    
    Args:
        post_id: 삭제할 게시글 ID
    
    Returns:
        삭제 결과
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            return {"error": f"ID {post_id}인 게시글을 찾을 수 없습니다."}
        
        db.delete(post)
        db.commit()
        
        return {
            "success": True,
            "message": f"게시글 ID {post_id}가 성공적으로 삭제되었습니다."
        }
    
    except SQLAlchemyError as e:
        db.rollback()
        return {"error": f"데이터베이스 오류: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def get_database_stats() -> Dict[str, Any]:
    """
    데이터베이스 통계 정보를 조회합니다.
    
    Returns:
        데이터베이스 통계
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_posts = db.query(Post).count()
        published_posts = db.query(Post).filter(Post.is_published == True).count()
        
        # 최근 활동
        recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
        recent_posts = db.query(Post).order_by(Post.created_at.desc()).limit(5).all()
        
        return {
            "statistics": {
                "total_users": total_users,
                "active_users": active_users,
                "total_posts": total_posts,
                "published_posts": published_posts,
                "draft_posts": total_posts - published_posts
            },
            "recent_activity": {
                "recent_users": [
                    {
                        "id": user.id,
                        "username": user.username,
                        "created_at": user.created_at.isoformat()
                    } for user in recent_users
                ],
                "recent_posts": [
                    {
                        "id": post.id,
                        "title": post.title,
                        "author": post.author.username,
                        "created_at": post.created_at.isoformat()
                    } for post in recent_posts
                ]
            }
        }
    
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def search_posts(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    게시글을 검색합니다.
    
    Args:
        query: 검색어 (제목과 내용에서 검색)
        limit: 검색 결과 수 제한
    
    Returns:
        검색 결과
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        posts = db.query(Post).filter(
            (Post.title.ilike(f"%{query}%")) | 
            (Post.content.ilike(f"%{query}%"))
        ).order_by(Post.created_at.desc()).limit(limit).all()
        
        search_results = []
        for post in posts:
            search_results.append({
                "id": post.id,
                "title": post.title,
                "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
                "is_published": post.is_published,
                "created_at": post.created_at.isoformat(),
                "author": {
                    "id": post.author.id,
                    "username": post.author.username,
                    "full_name": post.author.full_name
                }
            })
        
        return {
            "query": query,
            "results": search_results,
            "total_found": len(search_results)
        }
    
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def execute_raw_query(query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    원시 SQL 쿼리를 직접 실행합니다.
    
    Args:
        query: 실행할 SQL 쿼리
        params: 쿼리 매개변수 (선택사항)
    
    Returns:
        쿼리 결과
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        # SELECT 쿼리인지 확인
        query_lower = query.strip().lower()
        is_select = query_lower.startswith('select')
        
        if params:
            result = db.execute(text(query), params)
        else:
            result = db.execute(text(query))
        
        if is_select:
            # SELECT 쿼리의 경우 결과를 반환
            rows = result.fetchall()
            columns = result.keys() if hasattr(result, 'keys') else []
            
            return {
                "success": True,
                "columns": list(columns),
                "rows": [dict(zip(columns, row)) for row in rows],
                "row_count": len(rows)
            }
        else:
            # INSERT, UPDATE, DELETE 등의 경우
            db.commit()
            return {
                "success": True,
                "affected_rows": result.rowcount,
                "message": "쿼리가 성공적으로 실행되었습니다"
            }
            
    except Exception as e:
        db.rollback()
        return {"error": f"쿼리 실행 중 오류 발생: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def get_table_schema(table_name: str) -> Dict[str, Any]:
    """
    테이블의 스키마 정보를 조회합니다.
    
    Args:
        table_name: 조회할 테이블 이름
    
    Returns:
        테이블 스키마 정보
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        # PostgreSQL 시스템 테이블을 이용한 스키마 조회
        query = text("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """)
        
        result = db.execute(query, {"table_name": table_name})
        columns = result.fetchall()
        
        if not columns:
            return {"error": f"테이블 '{table_name}'을 찾을 수 없습니다"}
        
        schema_info = []
        for col in columns:
            schema_info.append({
                "column_name": col[0],
                "data_type": col[1],
                "is_nullable": col[2],
                "column_default": col[3],
                "max_length": col[4]
            })
        
        return {
            "success": True,
            "table_name": table_name,
            "columns": schema_info
        }
        
    except Exception as e:
        return {"error": f"스키마 조회 중 오류 발생: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def list_tables() -> Dict[str, Any]:
    """
    데이터베이스의 모든 테이블 목록을 조회합니다.
    
    Returns:
        테이블 목록
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    try:
        query = text("""
            SELECT table_name, table_type
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        result = db.execute(query)
        tables = result.fetchall()
        
        table_list = []
        for table in tables:
            table_list.append({
                "table_name": table[0],
                "table_type": table[1]
            })
        
        return {
            "success": True,
            "tables": table_list,
            "count": len(table_list)
        }
        
    except Exception as e:
        return {"error": f"테이블 목록 조회 중 오류 발생: {str(e)}"}
    
    finally:
        db.close()


@mcp.tool()
async def execute_analytics_query(query_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    미리 정의된 분석 쿼리를 실행합니다.
    
    Args:
        query_type: 쿼리 유형 (user_activity, post_trends, popular_users, recent_activity)
        params: 쿼리 매개변수
    
    Returns:
        분석 결과
    """
    db = get_db_session()
    if db is None:
        return {"error": "데이터베이스 연결에 실패했습니다."}
    
    params = params or {}
    
    # 미리 정의된 분석 쿼리들
    queries = {
        "user_activity": """
            SELECT 
                u.username,
                u.email,
                COUNT(p.id) as post_count,
                MAX(p.created_at) as last_post_date,
                MIN(p.created_at) as first_post_date
            FROM users u
            LEFT JOIN posts p ON u.id = p.user_id
            GROUP BY u.id, u.username, u.email
            ORDER BY post_count DESC
        """,
        
        "post_trends": """
            SELECT 
                DATE(created_at) as post_date,
                COUNT(*) as posts_count,
                COUNT(DISTINCT user_id) as active_users
            FROM posts
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY post_date DESC
        """,
        
        "popular_users": """
            SELECT 
                u.username,
                COUNT(p.id) as post_count,
                AVG(LENGTH(p.content)) as avg_post_length
            FROM users u
            INNER JOIN posts p ON u.id = p.user_id
            GROUP BY u.id, u.username
            HAVING COUNT(p.id) > 0
            ORDER BY post_count DESC
            LIMIT :limit
        """,
        
        "recent_activity": """
            SELECT 
                p.title,
                p.created_at,
                u.username,
                LENGTH(p.content) as content_length
            FROM posts p
            INNER JOIN users u ON p.user_id = u.id
            ORDER BY p.created_at DESC
            LIMIT :limit
        """
    }
    
    if query_type not in queries:
        return {
            "error": f"지원되지 않는 쿼리 유형: {query_type}",
            "available_types": list(queries.keys())
        }
    
    try:
        query = text(queries[query_type])
        
        # 기본 매개변수 설정
        if query_type in ["popular_users", "recent_activity"]:
            if "limit" not in params:
                params["limit"] = 10
        
        result = db.execute(query, params)
        rows = result.fetchall()
        columns = result.keys() if hasattr(result, 'keys') else []
        
        return {
            "success": True,
            "query_type": query_type,
            "columns": list(columns),
            "data": [dict(zip(columns, row)) for row in rows],
            "row_count": len(rows)
        }
        
    except Exception as e:
        return {"error": f"분석 쿼리 실행 중 오류 발생: {str(e)}"}
    
    finally:
        db.close()


if __name__ == "__main__":
    print("Database MCP Server 시작 중...")
    print("데이터베이스 연결을 확인합니다...")
    
    if init_database():
        print("✓ 데이터베이스 연결 성공")
        print("\n사용 가능한 도구들:")
        print("- create_user: 새로운 사용자 생성")
        print("- get_users: 사용자 목록 조회")
        print("- get_user_by_id: 사용자 상세 정보 조회")
        print("- create_post: 새로운 게시글 생성")
        print("- get_posts: 게시글 목록 조회")
        print("- update_post: 게시글 수정")
        print("- delete_post: 게시글 삭제")
        print("- get_database_stats: 데이터베이스 통계")
        print("- search_posts: 게시글 검색")
        print("- execute_raw_query: 원시 SQL 쿼리 실행")
        print("- get_table_schema: 테이블 스키마 조회")
        print("- list_tables: 테이블 목록 조회")
        print("- execute_analytics_query: 분석 쿼리 실행")
        print("\n환경변수 설정:")
        print("- DATABASE_URL: PostgreSQL 연결 문자열")
        print("  기본값: postgresql://postgres:password@localhost:5432/fastmcp_db")
        print()
        
        mcp.run()
    else:
        print("✗ 데이터베이스 연결 실패")
        print("PostgreSQL이 실행 중인지 확인하고 DATABASE_URL 환경변수를 설정하세요.")
        print("예: DATABASE_URL=postgresql://username:password@localhost:5432/database_name")
