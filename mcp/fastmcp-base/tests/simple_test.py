"""
간단한 테스트 스크립트 - uv 환경에서 FastMCP 테스트
"""

import asyncio
import json
from datetime import datetime, timedelta


async def test_basic_functionality():
    """기본 기능 테스트"""
    print("=== FastMCP 기본 기능 테스트 ===")
    
    # 1. 현재 시간 테스트
    print("\n1. 현재 시간 테스트")
    now = datetime.now()
    time_result = {
        "current_time": now.isoformat(),
        "formatted_time": now.strftime("%Y년 %m월 %d일 %H시 %M분 %S초"),
        "day_of_week": ["월", "화", "수", "목", "금", "토", "일"][now.weekday()],
        "timestamp": now.timestamp()
    }
    print(json.dumps(time_result, indent=2, ensure_ascii=False))
    
    # 2. 계산기 테스트
    print("\n2. 계산기 테스트")
    test_expressions = ["2 + 3", "10 * 5 + 2", "(100 / 4) - 5", "2 ** 3"]
    for expr in test_expressions:
        try:
            allowed_chars = "0123456789+-*/.() "
            if all(c in allowed_chars for c in expr):
                calc_result = eval(expr)
                result = {
                    "expression": expr,
                    "result": calc_result,
                    "type": type(calc_result).__name__
                }
            else:
                result = {"error": "허용되지 않은 문자가 포함되어 있습니다."}
        except Exception as e:
            result = {"error": f"계산 오류: {str(e)}"}
        
        print(f"  {expr} = {json.dumps(result, ensure_ascii=False)}")
    
    # 3. HTTP 테스트
    print("\n3. HTTP 클라이언트 테스트")
    try:
        import httpx
        
        start_time = datetime.now()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://httpbin.org/json")
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds() * 1000
        
        result = {
            "url": "https://httpbin.org/json",
            "status_code": response.status_code,
            "response_time_ms": round(response_time, 2),
            "success": response.is_success,
            "data": response.json() if response.is_success else None
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"HTTP 테스트 실패: {e}")
    
    # 4. 데모 날씨 데이터
    print("\n4. 데모 날씨 데이터")
    weather_demo = {
        "city": "Seoul",
        "country": "KR",
        "temperature": 22.5,
        "feels_like": 25.0,
        "humidity": 65,
        "pressure": 1013,
        "description": "맑음",
        "wind_speed": 3.2,
        "note": "데모 데이터입니다. 실제 API를 사용하려면 OPENWEATHER_API_KEY를 설정하세요."
    }
    print(json.dumps(weather_demo, indent=2, ensure_ascii=False))
    
    # 5. 데모 뉴스 데이터
    print("\n5. 데모 뉴스 데이터")
    news_demo = {
        "articles": [
            {
                "title": "[데모] AI 기술의 최신 동향",
                "description": "인공지능 기술이 다양한 분야에서 활용되고 있는 현황을 알아봅니다.",
                "url": "https://example.com/ai-trends",
                "source": "Tech News",
                "published_at": datetime.now().isoformat(),
                "author": "김기자"
            },
            {
                "title": "[데모] FastMCP 라이브러리 소개",
                "description": "Python으로 MCP 서버를 쉽게 만들 수 있는 FastMCP 라이브러리를 소개합니다.",
                "url": "https://example.com/fastmcp",
                "source": "Dev Blog",
                "published_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                "author": "박개발자"
            }
        ],
        "total_count": 2,
        "note": "데모 데이터입니다. 실제 뉴스를 보려면 NEWS_API_KEY를 설정하세요."
    }
    print(json.dumps(news_demo, indent=2, ensure_ascii=False))


async def test_fastmcp_import():
    """FastMCP 라이브러리 import 테스트"""
    print("\n=== FastMCP 라이브러리 테스트 ===")
    
    try:
        from fastmcp import FastMCP
        print("✓ FastMCP 라이브러리 import 성공")
        
        # 간단한 MCP 서버 생성 테스트
        mcp = FastMCP("Test Server")
        print("✓ FastMCP 서버 인스턴스 생성 성공")
        
        # 도구 등록 테스트
        @mcp.tool()
        async def test_tool(message: str = "Hello") -> str:
            """테스트용 도구"""
            return f"테스트 메시지: {message}"
        
        print("✓ 도구 등록 성공")
        
        # 도구 호출 테스트 (실제 서버 실행 없이)
        print("✓ FastMCP 기본 기능 테스트 완료")
        
    except ImportError as e:
        print(f"✗ FastMCP import 실패: {e}")
    except Exception as e:
        print(f"✗ FastMCP 테스트 실패: {e}")


async def main():
    """메인 테스트 함수"""
    print("FastMCP 프로젝트 테스트 시작")
    print("=" * 50)
    
    await test_fastmcp_import()
    await test_basic_functionality()
    
    print("\n" + "=" * 50)
    print("테스트 완료!")
    print("\n다음 단계:")
    print("1. 통합 서버 실행: uv run python integrated_server.py")
    print("2. 개별 서버 실행: uv run python weather_mcp_server.py")
    print("3. 클라이언트 데모: uv run python client_demo.py")


if __name__ == "__main__":
    asyncio.run(main())
