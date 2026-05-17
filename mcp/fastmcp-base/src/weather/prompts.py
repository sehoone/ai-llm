from src.core.mcp import mcp


@mcp.prompt()
def weather_analysis(city: str) -> str:
    """특정 도시의 날씨를 분석하고 외출 여부를 권고하는 프롬프트"""
    return (
        f"{city}의 현재 날씨와 5일 예보를 조회한 뒤, "
        f"기온·습도·강수 확률을 종합해 오늘 외출 여부와 준비물을 추천해주세요."
    )


@mcp.prompt()
def weather_comparison(cities: str) -> str:
    """여러 도시의 날씨를 비교하는 프롬프트"""
    return (
        f"다음 도시들의 현재 날씨를 각각 조회하고 비교 분석해주세요: {cities}\n"
        "기온, 습도, 날씨 상태를 표로 정리하고 가장 좋은 날씨의 도시를 추천해주세요."
    )
