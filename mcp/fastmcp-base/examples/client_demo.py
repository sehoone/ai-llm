"""
MCP 클라이언트 예제 - 서버와 통신하여 도구를 사용하는 방법을 보여줍니다.
"""

import asyncio
import json
from typing import Dict, Any


class MCPClient:
    """간단한 MCP 클라이언트 시뮬레이터"""
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.tools = {}
    
    def register_tool(self, name: str, func, description: str):
        """도구를 등록합니다."""
        self.tools[name] = {
            "function": func,
            "description": description
        }
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """등록된 도구를 호출합니다."""
        if tool_name not in self.tools:
            return {"error": f"도구 '{tool_name}'을 찾을 수 없습니다."}
        
        try:
            result = await self.tools[tool_name]["function"](**kwargs)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_tools(self) -> Dict[str, str]:
        """사용 가능한 도구 목록을 반환합니다."""
        return {name: tool["description"] for name, tool in self.tools.items()}


async def demo_weather_client():
    """날씨 MCP 서버 클라이언트 데모"""
    print("=== Weather MCP 클라이언트 데모 ===\n")
    
    # 날씨 서버에서 함수 import (실제로는 MCP 프로토콜 사용)
    from weather_mcp_server import get_weather, get_forecast, get_weather_alerts
    
    client = MCPClient("Weather Server")
    client.register_tool("get_weather", get_weather, "현재 날씨 조회")
    client.register_tool("get_forecast", get_forecast, "날씨 예보 조회")
    client.register_tool("get_weather_alerts", get_weather_alerts, "날씨 경보 조회")
    
    print("사용 가능한 도구:")
    for tool_name, description in client.list_tools().items():
        print(f"- {tool_name}: {description}")
    print()
    
    # 서울 현재 날씨 조회
    print("1. 서울 현재 날씨 조회")
    result = await client.call_tool("get_weather", city="Seoul", country_code="KR")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    # 부산 날씨 예보 조회
    print("2. 부산 날씨 예보 조회")
    result = await client.call_tool("get_forecast", city="Busan", country_code="KR", days=3)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    # 날씨 경보 조회
    print("3. 날씨 경보 조회")
    result = await client.call_tool("get_weather_alerts")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()


async def demo_news_client():
    """뉴스 MCP 서버 클라이언트 데모"""
    print("=== News MCP 클라이언트 데모 ===\n")
    
    # 뉴스 서버에서 함수 import (실제로는 MCP 프로토콜 사용)
    from news_mcp_server import get_top_headlines, search_news, get_news_sources, get_demo_news
    
    client = MCPClient("News Server")
    client.register_tool("get_top_headlines", get_top_headlines, "최신 헤드라인 뉴스")
    client.register_tool("search_news", search_news, "뉴스 검색")
    client.register_tool("get_news_sources", get_news_sources, "뉴스 소스 목록")
    client.register_tool("get_demo_news", get_demo_news, "데모 뉴스")
    
    print("사용 가능한 도구:")
    for tool_name, description in client.list_tools().items():
        print(f"- {tool_name}: {description}")
    print()
    
    # 데모 뉴스 조회 (API 키 없이도 동작)
    print("1. 데모 뉴스 조회")
    result = await client.call_tool("get_demo_news")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    # 기술 뉴스 검색
    print("2. '인공지능' 키워드로 뉴스 검색")
    result = await client.call_tool("search_news", query="인공지능", page_size=3)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    # 한국 기술 헤드라인
    print("3. 한국 기술 뉴스 헤드라인")
    result = await client.call_tool("get_top_headlines", country="kr", category="technology", page_size=3)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()


async def main():
    """메인 데모 실행"""
    print("FastMCP API 호출 예제 프로젝트")
    print("=" * 50)
    print()
    
    try:
        await demo_weather_client()
        print("\n" + "=" * 50 + "\n")
        await demo_news_client()
        
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")


if __name__ == "__main__":
    print("MCP 클라이언트 데모를 시작합니다...")
    print("참고: 실제 API 데이터를 보려면 환경변수를 설정하세요:")
    print("- OPENWEATHER_API_KEY: OpenWeatherMap API 키")
    print("- NEWS_API_KEY: NewsAPI 키")
    print()
    
    asyncio.run(main())
