import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.news.server import get_news_sources, get_top_headlines, search_news


@pytest.mark.asyncio
async def test_get_top_headlines_demo_mode():
    with patch("src.news.server.get_settings") as mock_settings:
        mock_settings.return_value.is_demo_news = True
        result = await get_top_headlines(country="kr")

    assert result["is_demo"] is True
    assert isinstance(result["articles"], list)
    assert result["total_results"] > 0


@pytest.mark.asyncio
async def test_get_top_headlines_with_api(mock_news_api_response):
    mock_response = MagicMock()
    mock_response.json.return_value = mock_news_api_response
    mock_response.raise_for_status = MagicMock()

    with (
        patch("src.news.server.get_settings") as mock_settings,
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value.is_demo_news = False
        mock_settings.return_value.news_api_key = "test_key"
        mock_settings.return_value.news_base_url = "https://newsapi.test.com/v2"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await get_top_headlines(country="kr")

    assert result["total_results"] == 1
    assert result["articles"][0]["title"] == "테스트 뉴스"
    assert result["articles"][0]["source"] == "Test Source"
    assert result.get("is_demo") is not True


@pytest.mark.asyncio
async def test_search_news_demo_mode():
    with patch("src.news.server.get_settings") as mock_settings:
        mock_settings.return_value.is_demo_news = True
        result = await search_news(query="AI")

    assert result["is_demo"] is True
    assert result["query"] == "AI"


@pytest.mark.asyncio
async def test_search_news_with_api(mock_news_api_response):
    mock_response = MagicMock()
    mock_response.json.return_value = mock_news_api_response
    mock_response.raise_for_status = MagicMock()

    with (
        patch("src.news.server.get_settings") as mock_settings,
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value.is_demo_news = False
        mock_settings.return_value.news_api_key = "test_key"
        mock_settings.return_value.news_base_url = "https://newsapi.test.com/v2"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await search_news(query="테스트")

    assert result["total_results"] == 1
    assert result["query"] == "테스트"


@pytest.mark.asyncio
async def test_article_missing_title_filtered(mock_news_api_response):
    mock_news_api_response["articles"].append(
        {"title": None, "description": None, "url": "", "source": {"name": ""}, "publishedAt": ""}
    )
    mock_response = MagicMock()
    mock_response.json.return_value = mock_news_api_response
    mock_response.raise_for_status = MagicMock()

    with (
        patch("src.news.server.get_settings") as mock_settings,
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value.is_demo_news = False
        mock_settings.return_value.news_api_key = "test_key"
        mock_settings.return_value.news_base_url = "https://newsapi.test.com/v2"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await get_top_headlines()

    assert all(a["title"] for a in result["articles"])
