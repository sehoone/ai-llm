"""Raw SQL read queries for the users domain."""
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def fetch_users(
    db: AsyncSession, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    rows = (
        await db.execute(
            text("""
                SELECT u.id, u.username, u.email, u.full_name, u.is_active, u.created_at,
                       COUNT(p.id) AS post_count
                FROM users u
                LEFT JOIN posts p ON p.author_id = u.id
                GROUP BY u.id
                ORDER BY u.id
                OFFSET :offset LIMIT :limit
            """),
            {"offset": offset, "limit": limit},
        )
    ).mappings().all()
    total = (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar_one()
    return [dict(r) for r in rows], total


async def fetch_user_by_id(
    db: AsyncSession, user_id: int
) -> Optional[dict[str, Any]]:
    row = (
        await db.execute(
            text("""
                SELECT id, username, email, full_name, is_active, created_at
                FROM users WHERE id = :user_id
            """),
            {"user_id": user_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def fetch_user_posts(
    db: AsyncSession, user_id: int
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text("""
                SELECT id, title, is_published, created_at
                FROM posts WHERE author_id = :user_id
                ORDER BY created_at DESC
            """),
            {"user_id": user_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def fetch_posts(
    db: AsyncSession, limit: int, offset: int, published_only: bool
) -> tuple[list[dict[str, Any]], int]:
    # published_only 필터를 파라미터로 처리 — f-string SQL 조합 방지
    rows = (
        await db.execute(
            text("""
                SELECT p.id, p.title, p.content, p.is_published,
                       p.created_at, p.updated_at,
                       u.id AS author_id, u.username AS author_username,
                       u.full_name AS author_full_name
                FROM posts p
                JOIN users u ON u.id = p.author_id
                WHERE (:published_only = FALSE OR p.is_published = TRUE)
                ORDER BY p.created_at DESC
                OFFSET :offset LIMIT :limit
            """),
            {"published_only": published_only, "offset": offset, "limit": limit},
        )
    ).mappings().all()
    total = (
        await db.execute(
            text("SELECT COUNT(*) FROM posts WHERE (:published_only = FALSE OR is_published = TRUE)"),
            {"published_only": published_only},
        )
    ).scalar_one()
    return [dict(r) for r in rows], total


async def search_posts_raw(
    db: AsyncSession, query: str, limit: int
) -> tuple[list[dict[str, Any]], int]:
    params = {"pattern": f"%{query}%", "limit": limit}
    rows = (
        await db.execute(
            text("""
                SELECT p.id, p.title, p.content, p.is_published,
                       p.created_at, p.updated_at,
                       u.id AS author_id, u.username AS author_username,
                       u.full_name AS author_full_name
                FROM posts p
                JOIN users u ON u.id = p.author_id
                WHERE p.title ILIKE :pattern OR p.content ILIKE :pattern
                ORDER BY p.created_at DESC
                LIMIT :limit
            """),
            params,
        )
    ).mappings().all()
    total = (
        await db.execute(
            text("""
                SELECT COUNT(*) FROM posts
                WHERE title ILIKE :pattern OR content ILIKE :pattern
            """),
            {"pattern": f"%{query}%"},
        )
    ).scalar_one()
    return [dict(r) for r in rows], total
