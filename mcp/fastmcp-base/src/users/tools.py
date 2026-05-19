import re
from datetime import datetime, timezone
from typing import Any, Optional

from fastmcp import Context
from fastmcp.exceptions import ToolError
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import SQLAlchemyError

from src.core.auth import protected
from src.core.config import get_settings
from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp
from src.users.models import (
    AuthorInfo,
    DatabaseStats,
    PostResponse,
    PostSummary,
    UserDetailResponse,
    UserResponse,
)
from src.users.orm import Post, User, utcnow

logger = get_logger("users.tools")

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_BLOCKED_SQL_KEYWORDS = frozenset({
    "drop", "delete", "update", "insert", "alter", "truncate",
    "create", "replace", "grant", "revoke",
})


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

    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            existing = await db.execute(
                select(User).where(or_(User.username == username, User.email == email))
            )
            if existing.scalar_one_or_none():
                raise ToolError("이미 존재하는 사용자명 또는 이메일입니다.")
            user = User(username=username, email=email, full_name=full_name)
            db.add(user)
            await db.flush()
            await db.refresh(user)
            await db.commit()
            return {"success": True, "user": _user_to_response(user, post_count=0).model_dump()}
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["limit", "offset"])
@protected
async def get_users(limit: int = 10, offset: int = 0, ctx: Context = None) -> dict[str, Any]:
    """사용자 목록을 조회합니다."""
    limit = min(max(1, limit), get_settings().db_max_page_size)
    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            users_stmt = (
                select(User, func.count(Post.id).label("post_count"))
                .outerjoin(Post, Post.author_id == User.id)
                .group_by(User.id)
                .order_by(User.id)
                .offset(offset)
                .limit(limit)
            )
            users_result = await db.execute(users_stmt)
            rows = users_result.all()
            total_result = await db.execute(select(func.count()).select_from(User))
            total = total_result.scalar_one()
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
    """ID로 사용자 정보를 조회합니다."""
    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                raise ToolError(f"ID {user_id}인 사용자를 찾을 수 없습니다.")
            posts_result = await db.execute(select(Post).where(Post.author_id == user_id))
            posts = posts_result.scalars().all()
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

    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            author_result = await db.execute(select(User).where(User.id == author_id))
            author = author_result.scalar_one_or_none()
            if not author:
                raise ToolError(f"ID {author_id}인 사용자를 찾을 수 없습니다.")
            post = Post(title=title, content=content, author_id=author_id, is_published=is_published)
            db.add(post)
            await db.flush()
            await db.refresh(post)
            await db.commit()
            return {"success": True, "post": _post_to_response(post, author).model_dump()}
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
    """게시글 목록을 조회합니다."""
    limit = min(max(1, limit), get_settings().db_max_page_size)
    preview_len = get_settings().content_preview_length
    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            q = select(Post, User).join(User, Post.author_id == User.id)
            if published_only:
                q = q.where(Post.is_published.is_(True))
            q = q.order_by(Post.created_at.desc()).offset(offset).limit(limit)
            result = await db.execute(q)
            rows = result.all()

            count_q = select(func.count()).select_from(Post)
            if published_only:
                count_q = count_q.where(Post.is_published.is_(True))
            total = (await db.execute(count_q)).scalar_one()

            posts_data = []
            for post, author in rows:
                d = _post_to_response(post, author).model_dump()
                d["content"] = _truncate(d["content"], preview_len)
                posts_data.append(d)
            return {"posts": posts_data, "total_count": total, "limit": limit, "offset": offset}
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

    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(Post, User).join(User, Post.author_id == User.id).where(Post.id == post_id)
            )
            row = result.first()
            if not row:
                raise ToolError(f"ID {post_id}인 게시글을 찾을 수 없습니다.")
            post, author = row
            if title is not None:
                post.title = title
            if content is not None:
                post.content = content
            if is_published is not None:
                post.is_published = is_published
            post.updated_at = utcnow()
            await db.flush()
            await db.refresh(post)
            await db.commit()
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
    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            result = await db.execute(select(Post).where(Post.id == post_id))
            post = result.scalar_one_or_none()
            if not post:
                raise ToolError(f"ID {post_id}인 게시글을 찾을 수 없습니다.")
            await db.delete(post)
            await db.commit()
            return {"success": True, "message": f"게시글 ID {post_id}가 삭제되었습니다."}
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger)
@protected
async def get_database_stats(ctx: Context) -> dict[str, Any]:
    """데이터베이스 통계 정보를 조회합니다."""
    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
            active_users = (await db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))).scalar_one()
            total_posts = (await db.execute(select(func.count()).select_from(Post))).scalar_one()
            published_posts = (await db.execute(select(func.count()).select_from(Post).where(Post.is_published.is_(True)))).scalar_one()

            stats = DatabaseStats(
                total_users=total_users,
                active_users=active_users,
                total_posts=total_posts,
                published_posts=published_posts,
                draft_posts=total_posts - published_posts,
            )
            recent_users = (await db.execute(select(User).order_by(User.created_at.desc()).limit(5))).scalars().all()
            recent_posts_result = await db.execute(
                select(Post, User).join(User).order_by(Post.created_at.desc()).limit(5)
            )
            recent_posts = recent_posts_result.all()
            return {
                "statistics": stats.model_dump(),
                "queried_at": datetime.now(timezone.utc).isoformat(),
                "recent_activity": {
                    "recent_users": [{"id": u.id, "username": u.username, "created_at": u.created_at.isoformat()} for u in recent_users],
                    "recent_posts": [{"id": p.id, "title": p.title, "author": a.username, "created_at": p.created_at.isoformat()} for p, a in recent_posts],
                },
            }
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["query", "limit"])
@protected
async def search_posts(query: str, ctx: Context, limit: int = 10) -> dict[str, Any]:
    """게시글을 검색합니다 (제목 + 내용)."""
    if not query.strip():
        raise ToolError("검색어를 입력해주세요.")
    limit = min(max(1, limit), get_settings().db_max_page_size)
    preview_len = get_settings().content_preview_length
    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(Post, User)
                .join(User, Post.author_id == User.id)
                .where(or_(Post.title.ilike(f"%{query}%"), Post.content.ilike(f"%{query}%")))
                .order_by(Post.created_at.desc())
                .limit(limit)
            )
            rows = result.all()
            results = []
            for post, author in rows:
                d = _post_to_response(post, author).model_dump()
                d["content"] = _truncate(d["content"], preview_len)
                results.append(d)
            return {"query": query, "results": results, "total_found": len(results)}
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


@mcp.tool()
@tool_logger(logger, param_keys=["query"])
@protected
async def execute_raw_query(
    query: str, ctx: Context, params: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """SELECT 쿼리를 실행합니다. 데이터 조회 전용 (쓰기 쿼리 불가)."""
    stripped = query.strip().lower()
    if not stripped.startswith("select"):
        raise ToolError("SELECT 쿼리만 허용됩니다.")
    for kw in _BLOCKED_SQL_KEYWORDS:
        if re.search(rf"\b{kw}\b", stripped):
            raise ToolError(f"허용되지 않는 SQL 키워드가 포함되어 있습니다: {kw}")

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
