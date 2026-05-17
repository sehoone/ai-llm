from src.core.config import get_settings
from src.core.mcp import mcp


@mcp.resource("weather://supported-units")
def get_supported_units() -> str:
    """지원하는 온도 단위 목록을 반환합니다."""
    return "metric (섭씨 °C), imperial (화씨 °F), standard (켈빈 K)"


@mcp.resource("weather://demo-info")
def get_demo_info() -> str:
    """데모 모드 안내 정보를 반환합니다."""
    settings = get_settings()
    mode = "데모 모드 (API 키 미설정)" if settings.is_demo_weather else "실제 API 모드"
    return f"현재 날씨 서버 모드: {mode}\n데모 모드에서는 고정 샘플 데이터를 반환합니다."
