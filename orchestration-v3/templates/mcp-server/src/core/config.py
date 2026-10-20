"""설정 — pydantic-settings. 단일 .env 로드 (apps/api 컨벤션과 동일)."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    # ── PostgreSQL (schema: llmonl) ──────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 8066
    postgres_db: str = "mydb"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # ── 사내 IdP (OIDC) — 인증 위임, 토큰 검증만 (ADR-0003) ────────────────────
    # 자체 토큰 발급 없음. IdP가 발급한 Bearer 토큰을 JWKS로 검증만 한다.
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_username_claim: str = "preferred_username"

    # ── sample 도메인: 외부 REST 시스템 ──────────────────────────────────────
    # 복제 후 실제 외부 시스템 값으로 교체. api_key가 demo_key면 데모 모드(외부 호출 없음).
    sample_base_url: str = "https://api.example.com"
    sample_api_key: str = Field(default="demo_key")

    # ── HTTP 클라이언트 ──────────────────────────────────────────────────────
    http_timeout: float = 10.0
    http_max_retries: int = 3

    # ── DB 페이지네이션 ──────────────────────────────────────────────────────
    db_max_page_size: int = 100

    # ── 로깅 ─────────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── MCP 서버 ─────────────────────────────────────────────────────────────
    mcp_transport: str = "streamable-http"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_workers: int = 1

    # 인증 모드 (HTTP transport)
    # "global"   : OIDCAuthMiddleware가 모든 MCP 요청 차단 (기본값)
    # "per-tool" : 미들웨어는 토큰 파싱만, @protected 도구가 직접 검증
    auth_mode: Literal["global", "per-tool"] = "global"

    @property
    def database_url(self) -> str:
        # psycopg3 (async 지원) — apps/api와 동일 드라이버
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_demo_sample(self) -> bool:
        """API 키 미설정 시 데모 모드 — 외부 호출 없이 고정 샘플 반환."""
        return self.sample_api_key in ("demo_key", "")


settings = Settings()
