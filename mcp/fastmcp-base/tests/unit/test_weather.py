import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.weather.server import get_forecast, get_weather


@pytest.mark.asyncio
async def test_get_weather_demo_mode():
    with patch("src.weather.server.get_settings") as mock_settings:
        mock_settings.return_value.is_demo_weather = True
        result = await get_weather("Seoul")

    assert result["city"] == "Seoul"
    assert result["is_demo"] is True
    assert "temperature" in result
    assert "humidity" in result


@pytest.mark.asyncio
async def test_get_weather_with_api(mock_weather_api_response):
    mock_response = MagicMock()
    mock_response.json.return_value = mock_weather_api_response
    mock_response.raise_for_status = MagicMock()

    with (
        patch("src.weather.server.get_settings") as mock_settings,
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value.is_demo_weather = False
        mock_settings.return_value.openweather_api_key = "test_key"
        mock_settings.return_value.openweather_base_url = "http://api.test.com"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await get_weather("Seoul", "KR")

    assert result["city"] == "Seoul"
    assert result["country"] == "KR"
    assert result["temperature"] == 22.5
    assert result["humidity"] == 65
    assert result.get("is_demo") is not True


@pytest.mark.asyncio
async def test_get_weather_city_not_found():
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 404
    http_error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)

    with (
        patch("src.weather.server.get_settings") as mock_settings,
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value.is_demo_weather = False
        mock_settings.return_value.openweather_api_key = "test_key"
        mock_settings.return_value.openweather_base_url = "http://api.test.com"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=http_error
        )

        result = await get_weather("NonExistentCity")

    assert "error" in result
    assert "NonExistentCity" in result["error"]


@pytest.mark.asyncio
async def test_get_forecast_demo_mode():
    with patch("src.weather.server.get_settings") as mock_settings:
        mock_settings.return_value.is_demo_weather = True
        result = await get_forecast("Seoul", days=3)

    assert result["city"] == "Seoul"
    assert result["is_demo"] is True
    assert len(result["forecasts"]) == 3


@pytest.mark.asyncio
async def test_get_forecast_days_clamped():
    with patch("src.weather.server.get_settings") as mock_settings:
        mock_settings.return_value.is_demo_weather = True
        result = await get_forecast("Seoul", days=10)

    assert len(result["forecasts"]) == 5


@pytest.mark.asyncio
async def test_get_forecast_with_api(mock_forecast_api_response):
    mock_response = MagicMock()
    mock_response.json.return_value = mock_forecast_api_response
    mock_response.raise_for_status = MagicMock()

    with (
        patch("src.weather.server.get_settings") as mock_settings,
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value.is_demo_weather = False
        mock_settings.return_value.openweather_api_key = "test_key"
        mock_settings.return_value.openweather_base_url = "http://api.test.com"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await get_forecast("Seoul", days=2)

    assert result["city"] == "Seoul"
    assert len(result["forecasts"]) == 2
