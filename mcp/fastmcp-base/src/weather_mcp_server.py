"""
Weather MCP Server - OpenWeatherMap API를 사용한 날씨 정보 조회 서버
"""

import asyncio
import os
from typing import Optional, Dict, Any
import httpx
from fastmcp import FastMCP
from pydantic import BaseModel


class WeatherQuery(BaseModel):
    """날씨 조회 요청 모델"""
    city: str
    country_code: Optional[str] = None


class ForecastQuery(BaseModel):
    """날씨 예보 조회 요청 모델"""
    city: str
    country_code: Optional[str] = None
    days: Optional[int] = 5


# MCP 서버 초기화
mcp = FastMCP("Weather MCP Server")

# OpenWeatherMap API 키 (환경변수에서 가져오기)
API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_api_key_here")
BASE_URL = "http://api.openweathermap.org/data/2.5"


@mcp.tool()
async def get_weather(city: str, country_code: Optional[str] = None) -> Dict[str, Any]:
    """
    특정 도시의 현재 날씨 정보를 조회합니다.
    
    Args:
        city: 도시 이름
        country_code: 국가 코드 (예: KR, US)
    
    Returns:
        날씨 정보 딕셔너리
    """
    try:
        location = city
        if country_code:
            location = f"{city},{country_code}"
        
        url = f"{BASE_URL}/weather"
        params = {
            "q": location,
            "appid": API_KEY,
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
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": f"도시 '{city}'를 찾을 수 없습니다."}
        return {"error": f"API 오류: {e.response.status_code}"}
    
    except Exception as e:
        return {"error": f"예상치 못한 오류: {str(e)}"}


@mcp.tool()
async def get_forecast(city: str, country_code: Optional[str] = None, days: int = 5) -> Dict[str, Any]:
    """
    특정 도시의 날씨 예보를 조회합니다.
    
    Args:
        city: 도시 이름
        country_code: 국가 코드 (예: KR, US)
        days: 예보 일수 (최대 5일)
    
    Returns:
        날씨 예보 정보
    """
    try:
        location = city
        if country_code:
            location = f"{city},{country_code}"
        
        url = f"{BASE_URL}/forecast"
        params = {
            "q": location,
            "appid": API_KEY,
            "units": "metric",
            "lang": "kr"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        # 일별로 데이터 그룹화 (3시간 간격 데이터를 하루 단위로)
        forecasts = []
        current_date = None
        daily_data = []
        
        for item in data["list"][:days * 8]:  # 8개 항목 = 하루 (3시간 * 8 = 24시간)
            date = item["dt_txt"][:10]  # YYYY-MM-DD
            
            if current_date != date:
                if daily_data:
                    # 하루의 평균 계산
                    avg_temp = sum(d["main"]["temp"] for d in daily_data) / len(daily_data)
                    forecasts.append({
                        "date": current_date,
                        "temperature": round(avg_temp, 1),
                        "description": daily_data[0]["weather"][0]["description"],
                        "humidity": daily_data[0]["main"]["humidity"],
                        "wind_speed": daily_data[0]["wind"]["speed"]
                    })
                
                current_date = date
                daily_data = [item]
            else:
                daily_data.append(item)
        
        # 마지막 날 처리
        if daily_data:
            avg_temp = sum(d["main"]["temp"] for d in daily_data) / len(daily_data)
            forecasts.append({
                "date": current_date,
                "temperature": round(avg_temp, 1),
                "description": daily_data[0]["weather"][0]["description"],
                "humidity": daily_data[0]["main"]["humidity"],
                "wind_speed": daily_data[0]["wind"]["speed"]
            })
        
        return {
            "city": data["city"]["name"],
            "country": data["city"]["country"],
            "forecasts": forecasts[:days]
        }
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": f"도시 '{city}'를 찾을 수 없습니다."}
        return {"error": f"API 오류: {e.response.status_code}"}
    
    except Exception as e:
        return {"error": f"예상치 못한 오류: {str(e)}"}


@mcp.tool()
async def get_weather_alerts() -> Dict[str, Any]:
    """
    날씨 경보 정보를 조회합니다 (데모용 정적 데이터).
    
    Returns:
        날씨 경보 정보
    """
    # 실제 구현시에는 기상청 API 등을 사용
    demo_alerts = [
        {
            "type": "강풍주의보",
            "region": "서울특별시",
            "description": "강한 바람이 예상됩니다.",
            "start_time": "2024-01-15 06:00",
            "end_time": "2024-01-15 18:00",
            "severity": "주의"
        },
        {
            "type": "대설경보",
            "region": "강원도",
            "description": "많은 눈이 예상됩니다.",
            "start_time": "2024-01-15 12:00",
            "end_time": "2024-01-16 06:00",
            "severity": "경보"
        }
    ]
    
    return {
        "alerts": demo_alerts,
        "total_count": len(demo_alerts),
        "updated_at": "2024-01-15 10:00:00"
    }


if __name__ == "__main__":
    print("Weather MCP Server 시작 중...")
    print("API 키 설정을 확인하세요: OPENWEATHER_API_KEY 환경변수")
    mcp.run()
