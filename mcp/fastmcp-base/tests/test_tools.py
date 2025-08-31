"""
MCP 도구 테스터 - 각 도구를 개별적으로 테스트할 수 있는 스크립트
"""

import asyncio
import json
import sys
from typing import Dict, Any


async def test_weather_tools():
    """날씨 관련 도구 테스트"""
    print("=== 날씨 도구 테스트 ===")
    
    try:
        from weather_mcp_server import get_weather, get_forecast, get_weather_alerts
        
        # 1. 날씨 조회 테스트
        print("\n1. 서울 날씨 조회 테스트")
        result = await get_weather("Seoul", "KR")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 2. 존재하지 않는 도시 테스트
        print("\n2. 존재하지 않는 도시 테스트")
        result = await get_weather("NonExistentCity")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 3. 날씨 예보 테스트
        print("\n3. 날씨 예보 테스트")
        result = await get_forecast("Seoul", "KR", 3)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 4. 날씨 경보 테스트
        print("\n4. 날씨 경보 테스트")
        result = await get_weather_alerts()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except ImportError as e:
        print(f"Import 오류: {e}")
    except Exception as e:
        print(f"테스트 실행 오류: {e}")


async def test_news_tools():
    """뉴스 관련 도구 테스트"""
    print("\n=== 뉴스 도구 테스트 ===")
    
    try:
        from news_mcp_server import get_top_headlines, search_news, get_news_sources, get_demo_news
        
        # 1. 데모 뉴스 테스트
        print("\n1. 데모 뉴스 테스트")
        result = await get_demo_news()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 2. 헤드라인 뉴스 테스트 (실제 API 키 필요)
        print("\n2. 헤드라인 뉴스 테스트")
        result = await get_top_headlines("kr", "technology", 3)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 3. 뉴스 검색 테스트
        print("\n3. 뉴스 검색 테스트")
        result = await search_news("AI", "ko", "publishedAt", 3)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 4. 뉴스 소스 테스트
        print("\n4. 뉴스 소스 테스트")
        result = await get_news_sources("technology", "ko", "kr")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except ImportError as e:
        print(f"Import 오류: {e}")
    except Exception as e:
        print(f"테스트 실행 오류: {e}")


async def test_integrated_tools():
    """통합 서버 도구 테스트"""
    print("\n=== 통합 서버 도구 테스트 ===")
    
    try:
        from integrated_server import get_weather, get_news, get_time, calculate, ping_server
        
        # 1. 날씨 조회 (데모 모드)
        print("\n1. 날씨 조회 (데모 모드)")
        result = await get_weather("Seoul", "KR")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 2. 뉴스 조회 (데모 모드)
        print("\n2. 뉴스 조회 (데모 모드)")
        result = await get_news("AI", "technology", 3)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 3. 현재 시간
        print("\n3. 현재 시간")
        result = await get_time()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 4. 계산기
        print("\n4. 계산기 테스트")
        test_expressions = ["2 + 3", "10 * 5 + 2", "(100 / 4) - 5", "2 ** 3"]
        for expr in test_expressions:
            result = await calculate(expr)
            print(f"  {expr} = {json.dumps(result, ensure_ascii=False)}")
        
        # 5. 잘못된 계산식
        print("\n5. 잘못된 계산식 테스트")
        result = await calculate("import os")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 6. 서버 핑 테스트
        print("\n6. 서버 핑 테스트")
        test_urls = ["https://www.google.com", "https://httpbin.org/status/200"]
        for url in test_urls:
            result = await ping_server(url)
            print(f"  {url}: {json.dumps(result, ensure_ascii=False)}")
        
    except ImportError as e:
        print(f"Import 오류: {e}")
    except Exception as e:
        print(f"테스트 실행 오류: {e}")


async def interactive_test():
    """대화형 테스트 모드"""
    print("\n=== 대화형 테스트 모드 ===")
    print("사용 가능한 명령어:")
    print("1. weather <도시명> - 날씨 조회")
    print("2. news <키워드> - 뉴스 검색")
    print("3. time - 현재 시간")
    print("4. calc <수식> - 계산")
    print("5. ping <URL> - 서버 핑")
    print("6. quit - 종료")
    print()
    
    try:
        from integrated_server import get_weather, get_news, get_time, calculate, ping_server
        
        while True:
            try:
                command = input("명령어를 입력하세요: ").strip()
                
                if command == "quit":
                    break
                
                if command == "time":
                    result = await get_time()
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                
                elif command.startswith("weather "):
                    city = command[8:].strip()
                    if city:
                        result = await get_weather(city)
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                    else:
                        print("도시명을 입력하세요.")
                
                elif command.startswith("news "):
                    keyword = command[5:].strip()
                    if keyword:
                        result = await get_news(keyword, count=3)
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                    else:
                        print("검색 키워드를 입력하세요.")
                
                elif command.startswith("calc "):
                    expression = command[5:].strip()
                    if expression:
                        result = await calculate(expression)
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                    else:
                        print("계산식을 입력하세요.")
                
                elif command.startswith("ping "):
                    url = command[5:].strip()
                    if url:
                        result = await ping_server(url)
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                    else:
                        print("URL을 입력하세요.")
                
                else:
                    print("알 수 없는 명령어입니다.")
                
                print()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"오류: {e}")
                
    except ImportError as e:
        print(f"통합 서버 모듈을 불러올 수 없습니다: {e}")


async def main():
    """메인 테스트 실행"""
    print("FastMCP 도구 테스터")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "weather":
            await test_weather_tools()
        elif test_type == "news":
            await test_news_tools()
        elif test_type == "integrated":
            await test_integrated_tools()
        elif test_type == "interactive":
            await interactive_test()
        else:
            print(f"알 수 없는 테스트 타입: {test_type}")
            print("사용법: python test_tools.py [weather|news|integrated|interactive]")
    else:
        # 모든 테스트 실행
        await test_weather_tools()
        await test_news_tools()
        await test_integrated_tools()
        
        # 대화형 모드 실행 여부 확인
        response = input("\n대화형 테스트를 실행하시겠습니까? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            await interactive_test()


if __name__ == "__main__":
    print("MCP 도구 테스터를 시작합니다...")
    print("환경변수 설정:")
    print("- OPENWEATHER_API_KEY: OpenWeatherMap API 키")
    print("- NEWS_API_KEY: NewsAPI 키")
    print("(설정하지 않으면 데모 데이터가 표시됩니다)")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n예상치 못한 오류: {e}")
