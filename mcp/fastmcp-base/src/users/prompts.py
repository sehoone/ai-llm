from src.core.mcp import mcp


@mcp.prompt()
def db_tool_guide() -> str:
    """데이터베이스 도구 사용 가이드"""
    return (
        "데이터베이스 도구 사용 가이드:\n"
        "- create_user: username(3-50자, 영문/숫자/언더스코어), email 필수\n"
        "- get_users: limit/offset으로 페이지네이션 (최대 100개)\n"
        "- get_user_by_id: 사용자 ID로 게시글 목록 포함 조회\n"
        "- create_post: title(1-200자), content(10,000자 이하), author_id 필수\n"
        "- get_posts: published_only=true로 공개 게시글만 필터링 가능\n"
        "- search_posts: 제목과 내용 전체 검색\n"
        "- execute_raw_query: SELECT만 허용, DROP/DELETE 등 불가\n"
        "- get_table_schema: 테이블명으로 컬럼 구조 확인\n"
        "- get_database_stats: 전체 통계 및 최근 활동 요약"
    )
