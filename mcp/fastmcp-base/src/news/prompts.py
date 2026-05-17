from src.core.mcp import mcp


@mcp.prompt()
def news_summary(topic: str) -> str:
    """특정 주제의 최신 뉴스를 요약하는 프롬프트"""
    return (
        f"'{topic}' 관련 최신 뉴스를 검색한 뒤, "
        f"핵심 내용을 3~5줄로 요약해주세요. "
        f"중요한 사실, 날짜, 출처를 포함해주세요."
    )


@mcp.prompt()
def daily_briefing(country: str = "kr") -> str:
    """일일 뉴스 브리핑 프롬프트"""
    return (
        f"{country} 기준 오늘의 헤드라인 뉴스를 카테고리별(정치, 경제, 기술, 스포츠)로 "
        f"조회하고, 각 카테고리에서 가장 중요한 뉴스 1개씩 골라 일일 브리핑을 작성해주세요."
    )
