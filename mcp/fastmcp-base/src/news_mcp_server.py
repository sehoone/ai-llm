"""
News MCP Server - NewsAPI를 사용한 뉴스 조회 서버
"""

import asyncio
import os
from typing import Optional, Dict, Any, List
import httpx
from fastmcp import FastMCP
from pydantic import BaseModel
from datetime import datetime, timedelta


class NewsQuery(BaseModel):
    """뉴스 조회 요청 모델"""
    query: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = "kr"
    page_size: Optional[int] = 10


# MCP 서버 초기화
mcp = FastMCP("News MCP Server")

# NewsAPI 키 (환경변수에서 가져오기)
API_KEY = os.getenv("NEWS_API_KEY", "your_api_key_here")
BASE_URL = "https://newsapi.org/v2"


@mcp.tool()
async def get_top_headlines(country: str = "kr", category: Optional[str] = None, page_size: int = 10) -> Dict[str, Any]:
    """
    최신 헤드라인 뉴스를 조회합니다.
    
    Args:
        country: 국가 코드 (kr, us 등)
        category: 뉴스 카테고리 (business, entertainment, general, health, science, sports, technology)
        page_size: 조회할 뉴스 개수 (최대 100)
    
    Returns:
        뉴스 목록
    """
    try:
        url = f"{BASE_URL}/top-headlines"
        params = {
            "apiKey": API_KEY,
            "country": country,
            "pageSize": min(page_size, 100)
        }
        
        if category:
            params["category"] = category
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data["status"] != "ok":
            return {"error": f"API 오류: {data.get('message', '알 수 없는 오류')}"}
        
        articles = []
        for article in data["articles"]:
            articles.append({
                "title": article["title"],
                "description": article["description"],
                "url": article["url"],
                "source": article["source"]["name"],
                "published_at": article["publishedAt"],
                "author": article.get("author", "Unknown")
            })
        
        return {
            "total_results": data["totalResults"],
            "articles": articles,
            "country": country,
            "category": category or "all"
        }
    
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP 오류: {e.response.status_code}"}
    
    except Exception as e:
        return {"error": f"예상치 못한 오류: {str(e)}"}


@mcp.tool()
async def search_news(query: str, language: str = "ko", sort_by: str = "publishedAt", page_size: int = 10) -> Dict[str, Any]:
    """
    키워드로 뉴스를 검색합니다.
    
    Args:
        query: 검색 키워드
        language: 언어 코드 (ko, en 등)
        sort_by: 정렬 기준 (relevancy, popularity, publishedAt)
        page_size: 조회할 뉴스 개수 (최대 100)
    
    Returns:
        검색된 뉴스 목록
    """
    try:
        url = f"{BASE_URL}/everything"
        
        # 최근 30일 내 뉴스만 검색
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        params = {
            "apiKey": API_KEY,
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(page_size, 100),
            "from": from_date
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data["status"] != "ok":
            return {"error": f"API 오류: {data.get('message', '알 수 없는 오류')}"}
        
        articles = []
        for article in data["articles"]:
            if article["title"] and article["description"]:  # 제목과 설명이 있는 기사만
                articles.append({
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"],
                    "source": article["source"]["name"],
                    "published_at": article["publishedAt"],
                    "author": article.get("author", "Unknown")
                })
        
        return {
            "query": query,
            "total_results": data["totalResults"],
            "articles": articles,
            "language": language,
            "sort_by": sort_by
        }
    
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP 오류: {e.response.status_code}"}
    
    except Exception as e:
        return {"error": f"예상치 못한 오류: {str(e)}"}


@mcp.tool()
async def get_news_sources(category: Optional[str] = None, language: str = "ko", country: str = "kr") -> Dict[str, Any]:
    """
    뉴스 소스 목록을 조회합니다.
    
    Args:
        category: 카테고리 필터
        language: 언어 코드
        country: 국가 코드
    
    Returns:
        뉴스 소스 목록
    """
    try:
        url = f"{BASE_URL}/sources"
        params = {
            "apiKey": API_KEY,
            "language": language,
            "country": country
        }
        
        if category:
            params["category"] = category
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data["status"] != "ok":
            return {"error": f"API 오류: {data.get('message', '알 수 없는 오류')}"}
        
        sources = []
        for source in data["sources"]:
            sources.append({
                "id": source["id"],
                "name": source["name"],
                "description": source["description"],
                "url": source["url"],
                "category": source["category"],
                "language": source["language"],
                "country": source["country"]
            })
        
        return {
            "sources": sources,
            "total_count": len(sources),
            "filters": {
                "category": category,
                "language": language,
                "country": country
            }
        }
    
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP 오류: {e.response.status_code}"}
    
    except Exception as e:
        return {"error": f"예상치 못한 오류: {str(e)}"}


@mcp.tool()
async def get_demo_news() -> Dict[str, Any]:
    """
    데모용 뉴스 데이터를 반환합니다 (API 키가 없을 때 사용).
    
    Returns:
        데모 뉴스 목록
    """
    demo_articles = [
        {
            "title": "[데모] AI 기술의 최신 동향",
            "description": "인공지능 기술이 다양한 분야에서 활용되고 있는 현황을 알아봅니다.",
            "url": "https://example.com/ai-trends",
            "source": "Tech News",
            "published_at": "2024-01-15T10:00:00Z",
            "author": "김기자"
        },
        {
            "title": "[데모] 파이썬 프로그래밍 팁",
            "description": "효율적인 파이썬 코딩을 위한 유용한 팁들을 소개합니다.",
            "url": "https://example.com/python-tips",
            "source": "Dev Blog",
            "published_at": "2024-01-15T09:30:00Z",
            "author": "박개발자"
        },
        {
            "title": "[데모] 웹 개발 트렌드 2024",
            "description": "2024년 웹 개발 분야의 주요 트렌드와 기술들을 살펴봅니다.",
            "url": "https://example.com/web-trends",
            "source": "Web Today",
            "published_at": "2024-01-15T08:45:00Z",
            "author": "이웹개발"
        }
    ]
    
    return {
        "total_results": len(demo_articles),
        "articles": demo_articles,
        "note": "이것은 데모 데이터입니다. 실제 뉴스를 보려면 NEWS_API_KEY 환경변수를 설정하세요."
    }


if __name__ == "__main__":
    print("News MCP Server 시작 중...")
    print("API 키 설정을 확인하세요: NEWS_API_KEY 환경변수")
    mcp.run()
