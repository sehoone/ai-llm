from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from fastmcp import Context
from fastmcp.exceptions import ToolError

from src.core.config import get_settings
from src.core.http import request_with_retry
from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp
from src.news.models import Article, NewsResponse, NewsSource, NewsSourcesResponse

logger = get_logger("news.tools")

_DEMO_ARTICLES = [
    Article(
        title="[데모] AI 기술의 최신 동향",
        description="인공지능 기술이 다양한 분야에서 활용되고 있는 현황을 알아봅니다.",
        url="https://example.com/ai-trends",
        source="Tech News",
        published_at="2024-01-15T10:00:00Z",
        author="김기자",
    ),
    Article(
        title="[데모] 파이썬 프로그래밍 팁",
        description="효율적인 파이썬 코딩을 위한 유용한 팁들을 소개합니다.",
        url="https://example.com/python-tips",
        source="Dev Blog",
        published_at="2024-01-15T09:30:00Z",
        author="박개발자",
    ),
    Article(
        title="[데모] 웹 개발 트렌드 2024",
        description="2024년 웹 개발 분야의 주요 트렌드와 기술들을 살펴봅니다.",
        url="https://example.com/web-trends",
        source="Web Today",
        published_at="2024-01-15T08:45:00Z",
        author="이웹개발",
    ),
]


def _parse_articles(raw: list[dict]) -> list[Article]:
    return [
        Article(
            title=a["title"],
            description=a.get("description"),
            url=a["url"],
            source=a["source"]["name"],
            published_at=a["publishedAt"],
            author=a.get("author"),
        )
        for a in raw
        if a.get("title")
    ]


@mcp.tool()
@tool_logger(logger, param_keys=["country", "category", "page_size"])
async def get_top_headlines(
    country: str = "kr",
    category: Optional[str] = None,
    page_size: int = 10,
    ctx: Context = None,
) -> dict[str, Any]:
    """최신 헤드라인 뉴스를 조회합니다."""
    settings = get_settings()

    if settings.is_demo_news:
        return NewsResponse(
            total_results=len(_DEMO_ARTICLES),
            articles=_DEMO_ARTICLES[:page_size],
            country=country,
            category=category or "all",
            is_demo=True,
        ).model_dump()

    try:
        params: dict[str, Any] = {
            "apiKey": settings.news_api_key,
            "country": country,
            "pageSize": min(page_size, 100),
        }
        if category:
            params["category"] = category

        client: httpx.AsyncClient = ctx.lifespan_context["http_client"]
        response = await request_with_retry(
            client, "GET", f"{settings.news_base_url}/top-headlines",
            settings.http_max_retries, params=params,
        )
        response.raise_for_status()
        data = response.json()

        if data["status"] != "ok":
            raise ToolError(data.get("message", "API 오류"))

        return NewsResponse(
            total_results=data["totalResults"],
            articles=_parse_articles(data["articles"]),
            country=country,
            category=category or "all",
        ).model_dump()
    except ToolError:
        raise
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP 오류: {e.response.status_code}")
    except Exception as e:
        logger.exception("get_top_headlines failed", extra={"country": country})
        raise ToolError(str(e))


@mcp.tool()
@tool_logger(logger, param_keys=["query", "language", "sort_by", "page_size"])
async def search_news(
    query: str,
    language: str = "ko",
    sort_by: str = "publishedAt",
    page_size: int = 10,
    ctx: Context = None,
) -> dict[str, Any]:
    """키워드로 뉴스를 검색합니다."""
    settings = get_settings()

    if settings.is_demo_news:
        filtered = [a for a in _DEMO_ARTICLES if query.lower() in (a.title or "").lower()]
        return NewsResponse(
            total_results=len(filtered),
            articles=filtered[:page_size],
            query=query,
            is_demo=True,
        ).model_dump()

    try:
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        params = {
            "apiKey": settings.news_api_key,
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(page_size, 100),
            "from": from_date,
        }
        client: httpx.AsyncClient = ctx.lifespan_context["http_client"]
        response = await request_with_retry(
            client, "GET", f"{settings.news_base_url}/everything",
            settings.http_max_retries, params=params,
        )
        response.raise_for_status()
        data = response.json()

        if data["status"] != "ok":
            raise ToolError(data.get("message", "API 오류"))

        return NewsResponse(
            total_results=data["totalResults"],
            articles=_parse_articles(data["articles"]),
            query=query,
        ).model_dump()
    except ToolError:
        raise
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP 오류: {e.response.status_code}")
    except Exception as e:
        logger.exception("search_news failed", extra={"query": query})
        raise ToolError(str(e))


@mcp.tool()
@tool_logger(logger, param_keys=["category", "language", "country"])
async def get_news_sources(
    category: Optional[str] = None,
    language: str = "ko",
    country: str = "kr",
    ctx: Context = None,
) -> dict[str, Any]:
    """뉴스 소스 목록을 조회합니다."""
    settings = get_settings()

    if settings.is_demo_news:
        return NewsSourcesResponse(sources=[], total_count=0).model_dump()

    try:
        params: dict[str, Any] = {
            "apiKey": settings.news_api_key,
            "language": language,
            "country": country,
        }
        if category:
            params["category"] = category

        client: httpx.AsyncClient = ctx.lifespan_context["http_client"]
        response = await request_with_retry(
            client, "GET", f"{settings.news_base_url}/sources",
            settings.http_max_retries, params=params,
        )
        response.raise_for_status()
        data = response.json()

        if data["status"] != "ok":
            raise ToolError(data.get("message", "API 오류"))

        sources = [
            NewsSource(
                id=s["id"],
                name=s["name"],
                description=s["description"],
                url=s["url"],
                category=s["category"],
                language=s["language"],
                country=s["country"],
            )
            for s in data["sources"]
        ]
        return NewsSourcesResponse(sources=sources, total_count=len(sources)).model_dump()
    except ToolError:
        raise
    except httpx.HTTPStatusError as e:
        raise ToolError(f"HTTP 오류: {e.response.status_code}")
    except Exception as e:
        logger.exception("get_news_sources failed")
        raise ToolError(str(e))
