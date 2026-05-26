import re
from typing import Any, Optional

from fastmcp import Context
from fastmcp.exceptions import ToolError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.core.auth import protected
from src.core.config import get_settings
from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp
from src.users.models import (
    AuthorInfo,
    PostResponse,
    PostSummary,
    UserDetailResponse,
    UserResponse,
)
from src.users.orm import Post, User
from src.users.service import UserService

logger = get_logger("users.tools")

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# ── 응답 변환 헬퍼 ──────────────────────────────────────────────────────────

def _user_to_response(user: User, post_count: int = 0) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        post_count=post_count,
    )


def _post_to_response(post: Post, author: User) -> PostResponse:
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content or "",
        is_published=post.is_published,
        created_at=post.created_at.isoformat(),
        updated_at=post.updated_at.isoformat(),
        author=AuthorInfo(
            id=author.id,
            username=author.username,
            full_name=author.full_name,
        ),
    )


def _truncate(content: str, max_len: int) -> str:
    return content[:max_len] + "..." if len(content) > max_len else content


def _row_to_user_response(row: dict) -> UserResponse:
    return UserResponse(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        full_name=row.get("full_name"),
        is_active=row["is_active"],
        created_at=row["created_at"].isoformat(),
        post_count=row.get("post_count", 0),
    )


def _row_to_post_summary(row: dict) -> PostSummary:
    return PostSummary(
        id=row["id"],
        title=row["title"],
        is_published=row["is_published"],
        created_at=row["created_at"].isoformat(),
    )


def _row_to_post_response(row: dict) -> PostResponse:
    return PostResponse(
        id=row["id"],
        title=row["title"],
        content=row.get("content") or "",
        is_published=row["is_published"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
        author=AuthorInfo(
            id=row["author_id"],
            username=row["author_username"],
            full_name=row.get("author_full_name"),
        ),
    )


# ── 쓰기 tools ──────────────────────────────────────────────────────────────

@mcp.tool()
@tool_logger(logger, param_keys=["username"])
@protected
async def create_user(
    username: str, email: str, ctx: Context, full_name: Optional[str] = None
) -> dict[str, Any]:
    """새로운 사용자를 생성합니다."""
    if not (3 <= len(username) <= 50):
        raise ToolError("username은 3~50자 사이여야 합니다.")
    if not _USERNAME_RE.match(username):
        raise ToolError("username은 영문자, 숫자, 언더스코어만 허용됩니다.")
    if not _EMAIL_RE.match(email) or len(email) > 100:
        raise ToolError("유효하지 않은 이메일 형식이거나 100자 초과입니다.")
    if full_name and len(full_name) > 100:
        raise ToolError("full_name은 100자 이하여야 합니다.")

    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        user = await svc.create_user(username, email, full_name)
        return {"success": True, "user": _user_to_response(user, post_count=0).model_dump()}
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["author_id", "is_published"])
@protected
async def create_post(
    title: str, content: str, author_id: int, ctx: Context, is_published: bool = False
) -> dict[str, Any]:
    """새로운 게시글을 생성합니다."""
    if not (1 <= len(title) <= 200):
        raise ToolError("title은 1~200자 사이여야 합니다.")
    if len(content) > 10000:
        raise ToolError("content는 10,000자 이하여야 합니다.")

    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        post, author = await svc.create_post(title, content, author_id, is_published)
        return {"success": True, "post": _post_to_response(post, author).model_dump()}
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["post_id", "is_published"])
@protected
async def update_post(
    post_id: int,
    ctx: Context,
    title: Optional[str] = None,
    content: Optional[str] = None,
    is_published: Optional[bool] = None,
) -> dict[str, Any]:
    """게시글을 수정합니다."""
    if title is not None and not (1 <= len(title) <= 200):
        raise ToolError("title은 1~200자 사이여야 합니다.")
    if content is not None and len(content) > 10000:
        raise ToolError("content는 10,000자 이하여야 합니다.")

    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        post, author = await svc.update_post(post_id, title, content, is_published)
        return {"success": True, "post": _post_to_response(post, author).model_dump()}
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["post_id"])
@protected
async def delete_post(post_id: int, ctx: Context) -> dict[str, Any]:
    """게시글을 삭제합니다."""
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        await svc.delete_post(post_id)
        return {"success": True, "message": f"게시글 ID {post_id}가 삭제되었습니다."}
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


# ── 읽기 tools (ORM) ────────────────────────────────────────────────────────

@mcp.tool()
@tool_logger(logger, param_keys=["limit", "offset"])
@protected
async def get_users(ctx: Context, limit: int = 10, offset: int = 0) -> dict[str, Any]:
    """사용자 목록을 조회합니다. (ORM)"""
    limit = min(max(1, limit), get_settings().db_max_page_size)
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        rows, total = await svc.list_users(limit, offset)
        return {
            "users": [_user_to_response(row.User, row.post_count).model_dump() for row in rows],
            "total_count": total,
            "limit": limit,
            "offset": offset,
        }
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["user_id"])
@protected
async def get_user_by_id(user_id: int, ctx: Context) -> dict[str, Any]:
    """ID로 사용자 정보를 조회합니다. (ORM)"""
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        user, posts = await svc.get_user(user_id)
        detail = UserDetailResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            posts=[
                PostSummary(id=p.id, title=p.title, is_published=p.is_published, created_at=p.created_at.isoformat())
                for p in posts
            ],
        )
        return {"user": detail.model_dump()}
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["limit", "offset", "published_only"])
@protected
async def get_posts(
    ctx: Context, limit: int = 10, offset: int = 0, published_only: bool = False
) -> dict[str, Any]:
    """게시글 목록을 조회합니다. (ORM)"""
    limit = min(max(1, limit), get_settings().db_max_page_size)
    preview_len = get_settings().content_preview_length
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        rows, total = await svc.list_posts(limit, offset, published_only)
        posts_data = []
        for post, author in rows:
            d = _post_to_response(post, author).model_dump()
            d["content"] = _truncate(d["content"], preview_len)
            posts_data.append(d)
        return {"posts": posts_data, "total_count": total, "limit": limit, "offset": offset}
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["query", "limit"])
@protected
async def search_posts(query: str, ctx: Context, limit: int = 10) -> dict[str, Any]:
    """게시글을 검색합니다 (제목 + 내용). (ORM)"""
    if not query.strip():
        raise ToolError("검색어를 입력해주세요.")
    limit = min(max(1, limit), get_settings().db_max_page_size)
    preview_len = get_settings().content_preview_length
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        rows, total = await svc.search_posts(query, limit)
        results = []
        for post, author in rows:
            d = _post_to_response(post, author).model_dump()
            d["content"] = _truncate(d["content"], preview_len)
            results.append(d)
        return {"query": query, "results": results, "total_found": total}
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


# ── 읽기 tools (raw SQL) ─────────────────────────────────────────────────────

@mcp.tool()
@tool_logger(logger, param_keys=["limit", "offset"])
@protected
async def get_users_sql(ctx: Context, limit: int = 10, offset: int = 0) -> dict[str, Any]:
    """사용자 목록을 조회합니다. (raw SQL)"""
    limit = min(max(1, limit), get_settings().db_max_page_size)
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        rows, total = await svc.list_users_sql(limit, offset)
        return {
            "users": [_row_to_user_response(row).model_dump() for row in rows],
            "total_count": total,
            "limit": limit,
            "offset": offset,
        }
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["user_id"])
@protected
async def get_user_by_id_sql(user_id: int, ctx: Context) -> dict[str, Any]:
    """ID로 사용자 정보를 조회합니다. (raw SQL)"""
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        user, posts = await svc.get_user_sql(user_id)
        detail = UserDetailResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            full_name=user.get("full_name"),
            is_active=user["is_active"],
            created_at=user["created_at"].isoformat(),
            posts=[_row_to_post_summary(p) for p in posts],
        )
        return {"user": detail.model_dump()}
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["limit", "offset", "published_only"])
@protected
async def get_posts_sql(
    ctx: Context, limit: int = 10, offset: int = 0, published_only: bool = False
) -> dict[str, Any]:
    """게시글 목록을 조회합니다. (raw SQL)"""
    limit = min(max(1, limit), get_settings().db_max_page_size)
    preview_len = get_settings().content_preview_length
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        rows, total = await svc.list_posts_sql(limit, offset, published_only)
        posts_data = []
        for row in rows:
            d = _row_to_post_response(row).model_dump()
            d["content"] = _truncate(d["content"], preview_len)
            posts_data.append(d)
        return {"posts": posts_data, "total_count": total, "limit": limit, "offset": offset}
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["query", "limit"])
@protected
async def search_posts_sql(query: str, ctx: Context, limit: int = 10) -> dict[str, Any]:
    """게시글을 검색합니다 (제목 + 내용). (raw SQL)"""
    if not query.strip():
        raise ToolError("검색어를 입력해주세요.")
    limit = min(max(1, limit), get_settings().db_max_page_size)
    preview_len = get_settings().content_preview_length
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        rows, total = await svc.search_posts_sql(query, limit)
        results = []
        for row in rows:
            d = _row_to_post_response(row).model_dump()
            d["content"] = _truncate(d["content"], preview_len)
            results.append(d)
        return {"query": query, "results": results, "total_found": total}
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


# ── 유틸리티 tools ───────────────────────────────────────────────────────────

@mcp.tool()
@tool_logger(logger)
@protected
async def get_database_stats(ctx: Context) -> dict[str, Any]:
    """데이터베이스 통계 정보를 조회합니다."""
    svc = UserService(ctx.lifespan_context["db_session"])
    try:
        return await svc.get_stats()
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["query"])
@protected
async def execute_raw_query(
    query: str, ctx: Context, params: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """SELECT 쿼리를 실행합니다. 데이터 조회 전용 (쓰기 쿼리 불가)."""
    if not query.strip().lower().startswith("select"):
        raise ToolError("SELECT 쿼리만 허용됩니다.")

    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            result = await db.execute(text(query), params or {})
            rows = result.fetchall()
            columns = list(result.keys())
            return {
                "success": True,
                "columns": columns,
                "rows": [dict(zip(columns, row)) for row in rows],
                "row_count": len(rows),
            }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"쿼리 실행 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["table_name"])
@protected
async def get_table_schema(table_name: str, ctx: Context) -> dict[str, Any]:
    """테이블의 컬럼 스키마 정보를 조회합니다."""
    if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
        raise ToolError("유효하지 않은 테이블명입니다.")
    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            result = await db.execute(
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
                raise ToolError(f"테이블 '{table_name}'을 찾을 수 없습니다.")
            return {"table": table_name, "columns": columns, "column_count": len(columns)}
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")
