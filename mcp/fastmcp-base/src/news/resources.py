from src.core.mcp import mcp


@mcp.resource("news://categories")
def get_news_categories() -> str:
    """NewsAPI에서 지원하는 뉴스 카테고리 목록을 반환합니다."""
    return "business, entertainment, general, health, science, sports, technology"


@mcp.resource("news://languages")
def get_news_languages() -> str:
    """지원하는 언어 코드 목록을 반환합니다."""
    return "ar, de, en, es, fr, he, it, nl, no, pt, ru, sv, ud, zh (한국어: ko)"
