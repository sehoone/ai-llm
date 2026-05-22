import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# APP_ENV 에 따라 로드할 .env 파일 결정
# 실행 예: APP_ENV=prod uv run python main.py server
_APP_ENV = os.getenv("APP_ENV", "local")
_ENV_FILE = f".env.{_APP_ENV}"


class Settings(BaseSettings):
    app_env: str = _APP_ENV

    openweather_api_key: str = Field(default="demo_key")
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"

    news_api_key: str = Field(default="demo_key")
    news_base_url: str = "https://newsapi.org/v2"

    database_url: str = Field(default="postgresql://postgres:password@localhost:5432/fastmcp_db")

    # HTTP 클라이언트
    http_timeout: float = 10.0
    http_max_retries: int = 3

    # 데이터베이스 페이지네이션
    db_page_size: int = 10
    db_max_page_size: int = 100
    content_preview_length: int = 200

    # 로깅
    log_level: str = "INFO"
    log_dir: Path = Path("logs")
    log_format: str = ""  # 비어있으면 app_env에 따라 자동 결정 (local→console, 그 외→json)

    # MCP 서버
    mcp_transport: str = "streamable-http"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_workers: int = 1

    # JWT (HTTP transport 전용)
    jwt_secret_key: str = Field(default="change-me-use-openssl-rand-hex-32")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # 인증 모드
    # "global"   : 미들웨어가 모든 MCP 요청을 차단 (기본값)
    # "per-tool" : 미들웨어는 토큰 파싱만, @require_auth 도구가 직접 검증
    auth_mode: Literal["global", "per-tool"] = "global"

    # 인증 사용자 — "username:password,username2:password2" 형식
    auth_users: str = Field(default="admin:admin123")

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def auth_users_dict(self) -> dict[str, str]:
        users: dict[str, str] = {}
        for pair in self.auth_users.split(","):
            pair = pair.strip()
            if ":" in pair:
                username, password = pair.split(":", 1)
                users[username.strip()] = password.strip()
        return users

    @property
    def is_demo_weather(self) -> bool:
        return self.openweather_api_key in ("demo_key", "your_openweather_api_key_here", "")

    @property
    def is_demo_news(self) -> bool:
        return self.news_api_key in ("demo_key", "your_newsapi_key_here", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
