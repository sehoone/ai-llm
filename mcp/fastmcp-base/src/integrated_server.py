"""
통합 MCP 서버 - 여러 기능을 하나의 서버에 통합
"""

import asyncio
import os
from typing import Optional, Dict, Any
import httpx
from fastmcp import FastMCP
from datetime import datetime, timedelta


# 통합 MCP 서버 초기화
mcp = FastMCP("Integrated MCP Server")

# API 키들
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "demo_key")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "demo_key")

# API 기본 URL들
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5"
NEWS_BASE_URL = "https://newsapi.org/v2"


# ===== 날씨 관련 도구들 =====

@mcp.tool()
async def get_weather(city: str, country_code: Optional[str] = None) -> Dict[str, Any]:
    """
    특정 도시의 현재 날씨 정보를 조회합니다.
    
    Args:
        city: 도시 이름
        country_code: 국가 코드 (예: KR, US)
    """
    if OPENWEATHER_API_KEY == "demo_key":
        return {
            "city": city,
            "country": country_code or "DEMO",
            "temperature": 22.5,
            "feels_like": 25.0,
            "humidity": 65,
            "pressure": 1013,
            "description": "맑음",
            "wind_speed": 3.2,
            "note": "데모 데이터입니다. OPENWEATHER_API_KEY를 설정하면 실제 데이터를 조회할 수 있습니다."
        }
    
    try:
        location = city
        if country_code:
            location = f"{city},{country_code}"
        
        url = f"{WEATHER_BASE_URL}/weather"
        params = {
            "q": location,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "kr"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        return {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
            "visibility": data.get("visibility", "N/A")
        }
    
    except Exception as e:
        return {"error": f"날씨 조회 실패: {str(e)}"}


@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> Dict[str, Any]:
    """
    특정 도시의 날씨 예보를 조회합니다.
    
    Args:
        city: 도시 이름
        days: 예보 일수 (1-5일)
    """
    if OPENWEATHER_API_KEY == "demo_key":
        forecasts = []
        for i in range(min(days, 5)):
            date = (datetime.now() + timedelta(days=i+1)).strftime("%Y-%m-%d")
            forecasts.append({
                "date": date,
                "temperature": 20 + i * 2,
                "description": ["맑음", "구름많음", "흐림", "비", "눈"][i % 5],
                "humidity": 60 + i * 5,
                "wind_speed": 2.0 + i * 0.5
            })
        
        return {
            "city": city,
            "forecasts": forecasts,
            "note": "데모 데이터입니다."
        }
    
    # 실제 API 호출 코드는 weather_mcp_server.py와 동일
    return {"error": "실제 API 구현 필요"}


# ===== 뉴스 관련 도구들 =====

@mcp.tool()
async def get_news(query: Optional[str] = None, category: Optional[str] = None, count: int = 5) -> Dict[str, Any]:
    """
    뉴스를 조회합니다.
    
    Args:
        query: 검색 키워드 (선택사항)
        category: 뉴스 카테고리 (business, technology, sports 등)
        count: 조회할 뉴스 개수
    """
    if NEWS_API_KEY == "demo_key":
        demo_articles = [
            {
                "title": f"[데모] {query or category or '일반'} 관련 뉴스 {i+1}",
                "description": f"이것은 {query or category or '일반'} 관련 데모 뉴스입니다.",
                "url": f"https://example.com/news-{i+1}",
                "source": "Demo News",
                "published_at": (datetime.now() - timedelta(hours=i)).isoformat(),
                "author": f"기자{i+1}"
            }
            for i in range(count)
        ]
        
        return {
            "query": query,
            "category": category,
            "articles": demo_articles,
            "note": "데모 데이터입니다. NEWS_API_KEY를 설정하면 실제 뉴스를 조회할 수 있습니다."
        }
    
    # 실제 API 호출 코드는 news_mcp_server.py와 동일
    return {"error": "실제 API 구현 필요"}


# ===== 유틸리티 도구들 =====

@mcp.tool()
async def get_time() -> Dict[str, Any]:
    """
    현재 시간 정보를 반환합니다.
    """
    now = datetime.now()
    return {
        "current_time": now.isoformat(),
        "formatted_time": now.strftime("%Y년 %m월 %d일 %H시 %M분 %S초"),
        "day_of_week": ["월", "화", "수", "목", "금", "토", "일"][now.weekday()],
        "timestamp": now.timestamp()
    }


@mcp.tool()
async def calculate(expression: str) -> Dict[str, Any]:
    """
    간단한 수학 계산을 수행합니다.
    
    Args:
        expression: 계산할 수식 (예: "2 + 3 * 4")
    """
    try:
        # 안전한 계산을 위해 허용된 문자만 사용
        allowed_chars = "0123456789+-*/.() "
        if not all(c in allowed_chars for c in expression):
            return {"error": "허용되지 않은 문자가 포함되어 있습니다."}
        
        result = eval(expression)
        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
    
    except Exception as e:
        return {"error": f"계산 오류: {str(e)}"}


@mcp.tool()
async def ping_server(url: str) -> Dict[str, Any]:
    """
    서버의 응답 시간을 확인합니다.
    
    Args:
        url: 확인할 URL
    """
    try:
        start_time = datetime.now()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
        
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000
        
        return {
            "url": url,
            "status_code": response.status_code,
            "response_time_ms": round(response_time, 2),
            "success": response.is_success,
            "headers": dict(response.headers)
        }
    
    except Exception as e:
        return {"error": f"핑 실패: {str(e)}"}


if __name__ == "__main__":
    print("통합 MCP 서버 시작 중...")
    print("\n사용 가능한 도구들:")
    print("- get_weather: 날씨 조회")
    print("- get_forecast: 날씨 예보")
    print("- get_news: 뉴스 조회")
    print("- get_time: 현재 시간")
    print("- calculate: 계산기")
    print("- ping_server: 서버 핑 테스트")
    print("\n환경변수 설정:")
    print("- OPENWEATHER_API_KEY: OpenWeatherMap API 키")
    print("- NEWS_API_KEY: NewsAPI 키")
    print()
    
    mcp.run()
