import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_weather_api_response():
    return {
        "name": "Seoul",
        "sys": {"country": "KR"},
        "main": {"temp": 22.5, "feels_like": 25.0, "humidity": 65, "pressure": 1013},
        "weather": [{"description": "맑음"}],
        "wind": {"speed": 3.2},
        "visibility": 10000,
    }


@pytest.fixture
def mock_forecast_api_response():
    return {
        "city": {"name": "Seoul", "country": "KR"},
        "list": [
            {
                "dt_txt": "2024-01-16 12:00:00",
                "main": {"temp": 20.0, "humidity": 60},
                "weather": [{"description": "맑음"}],
                "wind": {"speed": 3.0},
            },
            {
                "dt_txt": "2024-01-17 12:00:00",
                "main": {"temp": 18.0, "humidity": 65},
                "weather": [{"description": "구름많음"}],
                "wind": {"speed": 4.0},
            },
        ],
    }


@pytest.fixture
def mock_news_api_response():
    return {
        "status": "ok",
        "totalResults": 1,
        "articles": [
            {
                "title": "테스트 뉴스",
                "description": "테스트 설명",
                "url": "https://example.com/test",
                "source": {"name": "Test Source"},
                "publishedAt": "2024-01-15T10:00:00Z",
                "author": "테스트 기자",
            }
        ],
    }
