import asyncio
import re
from datetime import datetime
from typing import Any, Optional

from fastmcp import FastMCP
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import get_settings
from src.core.logging import get_logger, tool_logger
from src.database.models import (
    AuthorInfo,
    DatabaseStats,
    PostResponse,
    PostSummary,
    UserDetailResponse,
    UserResponse,
)
from src.database.orm import Post, User
from src.database.session import get_session, test_connection

logger = get_logger("database.server")
mcp = FastMCP("Database MCP Server")

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

_BLOCKED_SQL_KEYWORDS = frozenset({
    "drop", "delete", "update", "insert", "alter", "truncate",
    "create", "replace", "grant", "revoke",
})


# ─── 입력 검증 ────────────────────────────────────────────────────────────────

def _validate_username(username: str) -> Optional[str]:
    if not (3 <= len(username) <= 50):
        return "username은 3~50자 사이여야 합니다."
    if not _USERNAME_RE.match(username):
        return "username은 영문자, 숫자, 언더스코어만 허용됩니다."
    return None


def _validate_email(email: str) -> Optional[str]:
    if len(email) > 100:
        return "email은 100자 이하여야 합니다."
    if not _EMAIL_RE.match(email):
        return "유효하지 않은 이메일 형식입니다."
    return None


def _validate_raw_query(query: str) -> Optional[str]:
    stripped = query.strip().lower()
    if not stripped.startswith("select"):
        return "SELECT 쿼리만 허용됩니다."
    for kw in _BLOCKED_SQL_KEYWORDS:
        if re.search(rf"\b{kw}\b", stripped):
            return f"허용되지 않는 SQL 키워드가 포함되어 있습니다: {kw}"
    return None


# ─── ORM → Response 변환 ──────────────────────────────────────────────────────

def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        post_count=len(user.posts),
    )


def _post_to_response(post: Post) -> PostResponse:
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content or "",
        is_published=post.is_published,
        created_at=post.created_at.isoformat(),
        updated_at=post.updated_at.isoformat(),
        author=AuthorInfo(
            id=post.author.id,
            username=post.author.username,
            full_name=post.author.full_name,
        ),
    )


def _truncate_content(content: str, max_len: int) -> str:
    if len(content) > max_len:
        return content[:max_len] + "..."
    return content


# ─── 동기 DB 작업 함수 ────────────────────────────────────────────────────────

def _create_user_sync(username: str, email: str, full_name: Optional[str]) -> dict:
    try:
        with get_session() as db:
            if db.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first():
                return {"error": "이미 존재하는 사용자명 또는 이메일입니다."}
            user = User(username=username, email=email, full_name=full_name)
            db.add(user)
            db.flush()
            db.refresh(user)
            return {"success": True, "user": _user_to_response(user).model_dump()}
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


def _get_users_sync(limit: int, offset: int) -> dict:
    try:
        with get_session() as db:
            users = db.query(User).offset(offset).limit(limit).all()
            total = db.query(User).count()
            return {
                "users": [_user_to_response(u).model_dump() for u in users],
                "total_count": total,
                "limit": limit,
                "offset": offset,
            }
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


def _get_user_by_id_sync(user_id: int) -> dict:
    try:
        with get_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": f"ID {user_id}인 사용자를 찾을 수 없습니다."}
            detail = UserDetailResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                posts=[
                    PostSummary(
                        id=p.id,
                        title=p.title,
                        is_published=p.is_published,
                        created_at=p.created_at.isoformat(),
                    )
                    for p in user.posts
                ],
            )
            return {"user": detail.model_dump()}
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


def _create_post_sync(
    title: str, content: str, author_id: int, is_published: bool
) -> dict:
    try:
        with get_session() as db:
            author = db.query(User).filter(User.id == author_id).first()
            if not author:
                return {"error": f"ID {author_id}인 사용자를 찾을 수 없습니다."}
            post = Post(
                title=title, content=content, author_id=author_id, is_published=is_published
            )
            db.add(post)
            db.flush()
            db.refresh(post)
            return {"success": True, "post": _post_to_response(post).model_dump()}
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


def _get_posts_sync(limit: int, offset: int, published_only: bool) -> dict:
    preview_len = get_settings().content_preview_length
    try:
        with get_session() as db:
            query = db.query(Post)
            if published_only:
                query = query.filter(Post.is_published.is_(True))
            posts = query.order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
            total = query.count()
            summaries = []
            for p in posts:
                d = _post_to_response(p).model_dump()
                d["content"] = _truncate_content(d["content"], preview_len)
                summaries.append(d)
            return {
                "posts": summaries,
                "total_count": total,
                "limit": limit,
                "offset": offset,
            }
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


def _update_post_sync(
    post_id: int,
    title: Optional[str],
    content: Optional[str],
    is_published: Optional[bool],
) -> dict:
    try:
        with get_session() as db:
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                return {"error": f"ID {post_id}인 게시글을 찾을 수 없습니다."}
            if title is not None:
                post.title = title
            if content is not None:
                post.content = content
            if is_published is not None:
                post.is_published = is_published
            post.updated_at = datetime.utcnow()
            db.flush()
            db.refresh(post)
            return {"success": True, "post": _post_to_response(post).model_dump()}
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


def _delete_post_sync(post_id: int) -> dict:
    try:
        with get_session() as db:
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                return {"error": f"ID {post_id}인 게시글을 찾을 수 없습니다."}
            db.delete(post)
            return {"success": True, "message": f"게시글 ID {post_id}가 삭제되었습니다."}
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


def _get_stats_sync() -> dict:
    try:
        with get_session() as db:
            stats = DatabaseStats(
                total_users=db.query(User).count(),
                active_users=db.query(User).filter(User.is_active.is_(True)).count(),
                total_posts=db.query(Post).count(),
                published_posts=db.query(Post).filter(Post.is_published.is_(True)).count(),
                draft_posts=db.query(Post).filter(Post.is_published.is_(False)).count(),
            )
            recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
            recent_posts = db.query(Post).order_by(Post.created_at.desc()).limit(5).all()
            return {
                "statistics": stats.model_dump(),
                "queried_at": datetime.utcnow().isoformat(),
                "recent_activity": {
                    "recent_users": [
                        {
                            "id": u.id,
                            "username": u.username,
                            "created_at": u.created_at.isoformat(),
                        }
                        for u in recent_users
                    ],
                    "recent_posts": [
                        {
                            "id": p.id,
                            "title": p.title,
                            "author": p.author.username,
                            "created_at": p.created_at.isoformat(),
                        }
                        for p in recent_posts
                    ],
                },
            }
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


def _search_posts_sync(query: str, limit: int) -> dict:
    preview_len = get_settings().content_preview_length
    try:
        with get_session() as db:
            posts = (
                db.query(Post)
                .filter(Post.title.ilike(f"%{query}%") | Post.content.ilike(f"%{query}%"))
                .order_by(Post.created_at.desc())
                .limit(limit)
                .all()
            )
            results = []
            for p in posts:
                d = _post_to_response(p).model_dump()
                d["content"] = _truncate_content(d["content"], preview_len)
                results.append(d)
            return {"query": query, "results": results, "total_found": len(results)}
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


def _execute_raw_sync(query: str, params: Optional[dict]) -> dict:
    err = _validate_raw_query(query)
    if err:
        return {"error": err}
    try:
        with get_session() as db:
            result = db.execute(text(query), params or {})
            rows = result.fetchall()
            columns = list(result.keys())
            return {
                "success": True,
                "columns": columns,
                "rows": [dict(zip(columns, row)) for row in rows],
                "row_count": len(rows),
            }
    except Exception as e:
        return {"error": f"쿼리 실행 오류: {e}"}


def _get_table_schema_sync(table_name: str) -> dict:
    try:
        with get_session() as db:
            result = db.execute(
                text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = :table
                    ORDER BY ordinal_position
                """),
                {"table": table_name},
            )
            columns = [dict(row._mapping) for row in result]
            if not columns:
                return {"error": f"테이블 '{table_name}'을 찾을 수 없습니다."}
            return {"table": table_name, "columns": columns, "column_count": len(columns)}
    except SQLAlchemyError as e:
        return {"error": f"데이터베이스 오류: {e}"}


# ─── 비동기 MCP 도구 함수 ─────────────────────────────────────────────────────

@tool_logger(logger, param_keys=["username"])
async def create_user(
    username: str, email: str, full_name: Optional[str] = None
) -> dict[str, Any]:
    """새로운 사용자를 생성합니다."""
    if err := _validate_username(username):
        return {"error": err}
    if err := _validate_email(email):
        return {"error": err}
    if full_name and len(full_name) > 100:
        return {"error": "full_name은 100자 이하여야 합니다."}
    return await asyncio.to_thread(_create_user_sync, username, email, full_name)


@tool_logger(logger, param_keys=["limit", "offset"])
async def get_users(limit: int = 10, offset: int = 0) -> dict[str, Any]:
    """사용자 목록을 조회합니다."""
    limit = min(max(1, limit), get_settings().db_max_page_size)
    return await asyncio.to_thread(_get_users_sync, limit, offset)


@tool_logger(logger, param_keys=["user_id"])
async def get_user_by_id(user_id: int) -> dict[str, Any]:
    """ID로 사용자 정보를 조회합니다."""
    return await asyncio.to_thread(_get_user_by_id_sync, user_id)


@tool_logger(logger, param_keys=["author_id", "is_published"])
async def create_post(
    title: str, content: str, author_id: int, is_published: bool = False
) -> dict[str, Any]:
    """새로운 게시글을 생성합니다."""
    if not (1 <= len(title) <= 200):
        return {"error": "title은 1~200자 사이여야 합니다."}
    if len(content) > 10000:
        return {"error": "content는 10,000자 이하여야 합니다."}
    return await asyncio.to_thread(_create_post_sync, title, content, author_id, is_published)


@tool_logger(logger, param_keys=["limit", "offset", "published_only"])
async def get_posts(
    limit: int = 10, offset: int = 0, published_only: bool = False
) -> dict[str, Any]:
    """게시글 목록을 조회합니다."""
    limit = min(max(1, limit), get_settings().db_max_page_size)
    return await asyncio.to_thread(_get_posts_sync, limit, offset, published_only)


@tool_logger(logger, param_keys=["post_id", "is_published"])
async def update_post(
    post_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    is_published: Optional[bool] = None,
) -> dict[str, Any]:
    """게시글을 수정합니다."""
    if title is not None and not (1 <= len(title) <= 200):
        return {"error": "title은 1~200자 사이여야 합니다."}
    if content is not None and len(content) > 10000:
        return {"error": "content는 10,000자 이하여야 합니다."}
    return await asyncio.to_thread(_update_post_sync, post_id, title, content, is_published)


@tool_logger(logger, param_keys=["post_id"])
async def delete_post(post_id: int) -> dict[str, Any]:
    """게시글을 삭제합니다."""
    return await asyncio.to_thread(_delete_post_sync, post_id)


@tool_logger(logger)
async def get_database_stats() -> dict[str, Any]:
    """데이터베이스 통계 정보를 조회합니다."""
    return await asyncio.to_thread(_get_stats_sync)


@tool_logger(logger, param_keys=["query", "limit"])
async def search_posts(query: str, limit: int = 10) -> dict[str, Any]:
    """게시글을 검색합니다 (제목 + 내용)."""
    if not query.strip():
        return {"error": "검색어를 입력해주세요."}
    limit = min(max(1, limit), get_settings().db_max_page_size)
    return await asyncio.to_thread(_search_posts_sync, query, limit)


@tool_logger(logger, param_keys=["query"])
async def execute_raw_query(
    query: str, params: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """SELECT 쿼리를 실행합니다. 데이터 조회 전용 (쓰기 쿼리 불가)."""
    return await asyncio.to_thread(_execute_raw_sync, query, params)


@tool_logger(logger, param_keys=["table_name"])
async def get_table_schema(table_name: str) -> dict[str, Any]:
    """테이블의 컬럼 스키마 정보를 조회합니다."""
    if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
        return {"error": "유효하지 않은 테이블명입니다."}
    return await asyncio.to_thread(_get_table_schema_sync, table_name)


mcp.tool()(create_user)
mcp.tool()(get_users)
mcp.tool()(get_user_by_id)
mcp.tool()(create_post)
mcp.tool()(get_posts)
mcp.tool()(update_post)
mcp.tool()(delete_post)
mcp.tool()(get_database_stats)
mcp.tool()(search_posts)
mcp.tool()(execute_raw_query)
mcp.tool()(get_table_schema)
