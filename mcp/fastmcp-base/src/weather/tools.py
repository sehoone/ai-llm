from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from fastmcp import Context
from fastmcp.exceptions import ToolError

from src.core.config import get_settings
from src.core.http import request_with_retry
from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp
from src.weather.models import DailyForecast, ForecastResponse, WeatherResponse

logger = get_logger("weather.tools")


@mcp.tool()
@tool_logger(logger, param_keys=["city", "country_code"])
async def get_weather(
    city: str, country_code: Optional[str] = None, ctx: Context = None
) -> dict[str, Any]:
    """현재 날씨 정보를 조회합니다."""
    settings = get_settings()

    print(f"get_weather called with city={city}, country_code={country_code}")
    if settings.is_demo_weather:
        return WeatherResponse(
            city=city,
            country=country_code or "DEMO",
            temperature=22.5,
            feels_like=25.0,
            humidity=65,
            pressure=1013,
            description="맑음",
            wind_speed=3.2,
            is_demo=True,
        ).model_dump()

    try:
        location = f"{city},{country_code}" if country_code else city
        client: httpx.AsyncClient = ctx.lifespan_context["http_client"]
        print(f"get_weather API call: {settings.openweather_base_url}/weather with params: q={location}, appid={settings.openweather_api_key}, units=metric, lang=kr")
        response = await request_with_retry(
            client,
            "GET",
            f"{settings.openweather_base_url}/weather",
            settings.http_max_retries,
            params={"q": location, "appid": settings.openweather_api_key, "units": "metric", "lang": "kr"},
        )
        response.raise_for_status()
        data = response.json()
        return WeatherResponse(
            city=data["name"],
            country=data["sys"]["country"],
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            humidity=data["main"]["humidity"],
            pressure=data["main"]["pressure"],
            description=data["weather"][0]["description"],
            wind_speed=data["wind"]["speed"],
            visibility=data.get("visibility"),
        ).model_dump()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ToolError(f"도시 '{city}'를 찾을 수 없습니다.")
        raise ToolError(f"API 오류: {e.response.status_code}")
    except ToolError:
        raise
    except Exception as e:
        logger.exception("get_weather failed", city=city)
        raise ToolError(str(e))


@mcp.tool()
@tool_logger(logger, param_keys=["city", "country_code", "days"])
async def get_forecast(
    city: str, country_code: Optional[str] = None, days: int = 5, ctx: Context = None
) -> dict[str, Any]:
    """날씨 예보를 조회합니다 (최대 5일)."""
    settings = get_settings()
    days = max(1, min(days, 5))

    if settings.is_demo_weather:
        forecasts = [
            DailyForecast(
                date=(datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                temperature=round(20.0 + i * 2, 1),
                description=["맑음", "구름많음", "흐림", "비", "눈"][i % 5],
                humidity=60 + i * 5,
                wind_speed=round(2.0 + i * 0.5, 1),
            )
            for i in range(days)
        ]
        return ForecastResponse(city=city, country="DEMO", forecasts=forecasts, is_demo=True).model_dump()

    try:
        location = f"{city},{country_code}" if country_code else city
        client: httpx.AsyncClient = ctx.lifespan_context["http_client"]
        response = await request_with_retry(
            client,
            "GET",
            f"{settings.openweather_base_url}/forecast",
            settings.http_max_retries,
            params={"q": location, "appid": settings.openweather_api_key, "units": "metric", "lang": "kr"},
        )
        response.raise_for_status()
        data = response.json()

        daily: dict[str, list] = {}
        for item in data["list"]:
            daily.setdefault(item["dt_txt"][:10], []).append(item)

        forecasts = []
        for date, items in sorted(daily.items())[:days]:
            avg_temp = sum(i["main"]["temp"] for i in items) / len(items)
            forecasts.append(DailyForecast(
                date=date,
                temperature=round(avg_temp, 1),
                description=items[0]["weather"][0]["description"],
                humidity=items[0]["main"]["humidity"],
                wind_speed=items[0]["wind"]["speed"],
            ))

        return ForecastResponse(
            city=data["city"]["name"],
            country=data["city"]["country"],
            forecasts=forecasts,
        ).model_dump()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ToolError(f"도시 '{city}'를 찾을 수 없습니다.")
        raise ToolError(f"API 오류: {e.response.status_code}")
    except ToolError:
        raise
    except Exception as e:
        logger.exception("get_forecast failed", city=city)
        raise ToolError(str(e))
