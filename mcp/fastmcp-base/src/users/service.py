"""
Service layer — 비즈니스 로직 + 트랜잭션 경계
Spring @Service @Transactional 상당.

각 public 메서드 = 하나의 트랜잭션 단위.
  async with db.begin():
    - 진입 시 BEGIN
    - 정상 종료 시 자동 COMMIT
    - 예외 발생 시 자동 ROLLBACK  (ToolError 포함)
"""
from datetime import datetime, timezone
from typing import Any, Optional

from fastmcp.exceptions import ToolError
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.users.models import DatabaseStats
from src.users.orm import Post, User, utcnow
from src.users.sql import (
    fetch_posts,
    fetch_user_by_id,
    fetch_user_posts,
    fetch_users,
    search_posts_raw,
)


class UserService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    # ── 읽기: ORM ──────────────────────────────────────────────────────────

    async def list_users(self, limit: int, offset: int) -> tuple[list, int]:
        async with self._factory() as db:
            async with db.begin():
                rows = (await db.execute(
                    select(User, func.count(Post.id).label("post_count"))
                    .outerjoin(Post, Post.author_id == User.id)
                    .group_by(User.id)
                    .order_by(User.id)
                    .offset(offset)
                    .limit(limit)
                )).all()
                total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
                return rows, total

    async def get_user(self, user_id: int) -> tuple[User, list[Post]]:
        async with self._factory() as db:
            async with db.begin():
                user = (await db.execute(
                    select(User).where(User.id == user_id)
                )).scalar_one_or_none()
                if not user:
                    raise ToolError(f"ID {user_id}인 사용자를 찾을 수 없습니다.")
                posts = (await db.execute(
                    select(Post).where(Post.author_id == user_id)
                )).scalars().all()
                return user, posts

    async def list_posts(
        self, limit: int, offset: int, published_only: bool
    ) -> tuple[list, int]:
        async with self._factory() as db:
            async with db.begin():
                q = select(Post, User).join(User, Post.author_id == User.id)
                if published_only:
                    q = q.where(Post.is_published.is_(True))
                q = q.order_by(Post.created_at.desc()).offset(offset).limit(limit)
                rows = (await db.execute(q)).all()
                count_q = select(func.count()).select_from(Post)
                if published_only:
                    count_q = count_q.where(Post.is_published.is_(True))
                total = (await db.execute(count_q)).scalar_one()
                return rows, total

    async def search_posts(self, query: str, limit: int) -> tuple[list, int]:
        async with self._factory() as db:
            async with db.begin():
                f = or_(Post.title.ilike(f"%{query}%"), Post.content.ilike(f"%{query}%"))
                total = (await db.execute(
                    select(func.count()).select_from(Post).where(f)
                )).scalar_one()
                rows = (await db.execute(
                    select(Post, User)
                    .join(User, Post.author_id == User.id)
                    .where(f)
                    .order_by(Post.created_at.desc())
                    .limit(limit)
                )).all()
                return rows, total

    async def get_stats(self) -> dict[str, Any]:
        async with self._factory() as db:
            async with db.begin():
                user_row = (await db.execute(
                    select(
                        func.count().label("total"),
                        func.count(1).filter(User.is_active.is_(True)).label("active"),
                    ).select_from(User)
                )).one()
                post_row = (await db.execute(
                    select(
                        func.count().label("total"),
                        func.count(1).filter(Post.is_published.is_(True)).label("published"),
                    ).select_from(Post)
                )).one()
                stats = DatabaseStats(
                    total_users=user_row.total,
                    active_users=user_row.active,
                    total_posts=post_row.total,
                    published_posts=post_row.published,
                    draft_posts=post_row.total - post_row.published,
                )
                recent_users = (await db.execute(
                    select(User).order_by(User.created_at.desc()).limit(5)
                )).scalars().all()
                recent_posts = (await db.execute(
                    select(Post, User).join(User).order_by(Post.created_at.desc()).limit(5)
                )).all()
                return {
                    "statistics": stats.model_dump(),
                    "queried_at": datetime.now(timezone.utc).isoformat(),
                    "recent_activity": {
                        "recent_users": [
                            {"id": u.id, "username": u.username, "created_at": u.created_at.isoformat()}
                            for u in recent_users
                        ],
                        "recent_posts": [
                            {"id": p.id, "title": p.title, "author": a.username, "created_at": p.created_at.isoformat()}
                            for p, a in recent_posts
                        ],
                    },
                }

    # ── 읽기: raw SQL ──────────────────────────────────────────────────────

    async def list_users_sql(self, limit: int, offset: int) -> tuple[list[dict], int]:
        async with self._factory() as db:
            async with db.begin():
                return await fetch_users(db, limit, offset)

    async def get_user_sql(self, user_id: int) -> tuple[dict, list[dict]]:
        async with self._factory() as db:
            async with db.begin():
                user = await fetch_user_by_id(db, user_id)
                if not user:
                    raise ToolError(f"ID {user_id}인 사용자를 찾을 수 없습니다.")
                posts = await fetch_user_posts(db, user_id)
                return user, posts

    async def list_posts_sql(
        self, limit: int, offset: int, published_only: bool
    ) -> tuple[list[dict], int]:
        async with self._factory() as db:
            async with db.begin():
                return await fetch_posts(db, limit, offset, published_only)

    async def search_posts_sql(self, query: str, limit: int) -> tuple[list[dict], int]:
        async with self._factory() as db:
            async with db.begin():
                return await search_posts_raw(db, query, limit)

    # ── 쓰기 ────────────────────────────────────────────────────────────────

    async def create_user(
        self, username: str, email: str, full_name: Optional[str]
    ) -> User:
        async with self._factory() as db:
            async with db.begin():
                existing = (await db.execute(
                    select(User).where(or_(User.username == username, User.email == email))
                )).scalar_one_or_none()
                if existing:
                    raise ToolError("이미 존재하는 사용자명 또는 이메일입니다.")
                user = User(username=username, email=email, full_name=full_name)
                db.add(user)
                await db.flush()
                await db.refresh(user)
                return user  # db.begin() 종료 시 자동 COMMIT

    async def create_post(
        self, title: str, content: str, author_id: int, is_published: bool
    ) -> tuple[Post, User]:
        async with self._factory() as db:
            async with db.begin():
                author = (await db.execute(
                    select(User).where(User.id == author_id)
                )).scalar_one_or_none()
                if not author:
                    raise ToolError(f"ID {author_id}인 사용자를 찾을 수 없습니다.")
                post = Post(
                    title=title, content=content,
                    author_id=author_id, is_published=is_published,
                )
                db.add(post)
                await db.flush()
                await db.refresh(post)
                return post, author  # db.begin() 종료 시 자동 COMMIT

    async def update_post(
        self,
        post_id: int,
        title: Optional[str],
        content: Optional[str],
        is_published: Optional[bool],
    ) -> tuple[Post, User]:
        async with self._factory() as db:
            async with db.begin():
                row = (await db.execute(
                    select(Post, User)
                    .join(User, Post.author_id == User.id)
                    .where(Post.id == post_id)
                )).first()
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
                return post, author  # db.begin() 종료 시 자동 COMMIT

    async def delete_post(self, post_id: int) -> None:
        async with self._factory() as db:
            async with db.begin():
                post = (await db.execute(
                    select(Post).where(Post.id == post_id)
                )).scalar_one_or_none()
                if not post:
                    raise ToolError(f"ID {post_id}인 게시글을 찾을 수 없습니다.")
                await db.delete(post)
                # db.begin() 종료 시 자동 COMMIT
