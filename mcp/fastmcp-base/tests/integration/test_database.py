"""
통합 테스트 — PostgreSQL이 필요합니다.

DATABASE_URL 환경변수가 설정되어 있고 DB가 실행 중일 때만 실행됩니다.
"""

import pytest
from sqlalchemy import text

from src.database.session import get_session, test_connection
from src.database.server import (
    create_post,
    create_user,
    delete_post,
    get_database_stats,
    get_posts,
    get_user_by_id,
    get_users,
    search_posts,
    update_post,
)


def is_db_available() -> bool:
    return test_connection()


pytestmark = pytest.mark.skipif(
    not is_db_available(), reason="PostgreSQL이 실행 중이지 않습니다."
)

_PREFIX = "pytest_"


@pytest.fixture(autouse=True)
def cleanup_test_data():
    yield
    try:
        with get_session() as db:
            db.execute(
                text("DELETE FROM posts WHERE title LIKE :prefix"),
                {"prefix": f"{_PREFIX}%"},
            )
            db.execute(
                text("DELETE FROM users WHERE username LIKE :prefix"),
                {"prefix": f"{_PREFIX}%"},
            )
    except Exception:
        pass


@pytest.mark.asyncio
async def test_create_and_get_user():
    result = await create_user(
        username=f"{_PREFIX}user1",
        email=f"{_PREFIX}user1@test.com",
        full_name="테스트 유저",
    )
    assert result["success"] is True
    user = result["user"]
    assert user["username"] == f"{_PREFIX}user1"

    get_result = await get_user_by_id(user["id"])
    assert get_result["user"]["id"] == user["id"]


@pytest.mark.asyncio
async def test_create_user_duplicate():
    await create_user(username=f"{_PREFIX}dup", email=f"{_PREFIX}dup@test.com")
    result = await create_user(username=f"{_PREFIX}dup", email=f"{_PREFIX}dup@test.com")
    assert "error" in result


@pytest.mark.asyncio
async def test_create_and_delete_post():
    user_result = await create_user(
        username=f"{_PREFIX}postauthor", email=f"{_PREFIX}postauthor@test.com"
    )
    author_id = user_result["user"]["id"]

    post_result = await create_post(
        title=f"{_PREFIX}Test Post", content="테스트 내용입니다.",
        author_id=author_id, is_published=True,
    )
    assert post_result["success"] is True

    delete_result = await delete_post(post_result["post"]["id"])
    assert delete_result["success"] is True


@pytest.mark.asyncio
async def test_update_post():
    user_result = await create_user(
        username=f"{_PREFIX}updateauthor", email=f"{_PREFIX}updateauthor@test.com"
    )
    author_id = user_result["user"]["id"]

    post_result = await create_post(
        title=f"{_PREFIX}Original", content="원본 내용", author_id=author_id
    )
    post_id = post_result["post"]["id"]

    update_result = await update_post(post_id=post_id, title=f"{_PREFIX}Updated", is_published=True)
    assert update_result["success"] is True
    assert update_result["post"]["title"] == f"{_PREFIX}Updated"
    assert update_result["post"]["is_published"] is True


@pytest.mark.asyncio
async def test_search_posts():
    user_result = await create_user(
        username=f"{_PREFIX}searcher", email=f"{_PREFIX}searcher@test.com"
    )
    await create_post(
        title=f"{_PREFIX}FastMCP 소개", content="FastMCP 프레임워크 설명",
        author_id=user_result["user"]["id"],
    )

    result = await search_posts(query="FastMCP")
    assert result["total_found"] >= 1
    assert any("FastMCP" in r["title"] for r in result["results"])


@pytest.mark.asyncio
async def test_get_database_stats():
    result = await get_database_stats()
    assert "statistics" in result
    assert result["statistics"]["total_users"] >= 0


@pytest.mark.asyncio
async def test_get_users_pagination():
    result = await get_users(limit=5, offset=0)
    assert "users" in result
    assert len(result["users"]) <= 5
