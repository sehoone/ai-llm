from src.core.mcp import mcp


@mcp.resource("db://schema")
def get_db_schema() -> str:
    """데이터베이스 스키마 정보를 반환합니다."""
    return (
        "users: id(PK), username(unique), email(unique), full_name, is_active, created_at\n"
        "posts: id(PK), title, content, is_published, author_id(FK→users.id), created_at, updated_at"
    )


@mcp.resource("db://tables")
def get_db_tables() -> str:
    """사용 가능한 테이블 목록을 반환합니다."""
    return "users, posts"
