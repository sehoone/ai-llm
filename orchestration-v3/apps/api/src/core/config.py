from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"

    # PostgreSQL (schema: llmonl)
    postgres_host: str = "localhost"
    postgres_port: int = 8066
    postgres_db: str = "mydb"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # 자체 ID/PW 인증 — 백엔드가 직접 자격 검증 후 JWT(HS256) 발급.
    # (OIDC 위임에서 전환. 워크스페이스 규약대로 HS256 + 공유 시크릿.)
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # 최초 로그인용 seed 관리자 — 앱 기동 시 없으면 생성(ADR-0003 전환).
    # 비밀번호가 비어 있으면 seed 생성을 건너뛴다.
    seed_admin_username: str = "admin"
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = ""

    # 사내 IdP (OIDC) — 비활성(코드 보존). 자체 ID/PW 인증으로 전환됨.
    # 아래 설정은 OIDC 복귀 시 재사용(현재 미사용).
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_role_claim: str = "roles"
    oidc_username_claim: str = "preferred_username"
    oidc_email_claim: str = "email"

    # 챗 사용자 승인 (HITL — ADR-0008)
    chat_approval_ttl_seconds: int = 900  # 승인 대기 만료 (15분)
    chat_checkpointer: str = "memory"     # "memory"(인프로세스) | "postgres"(후속)

    # Langfuse (LLM 관측 — ADR-0007). self-host 또는 cloud. 키 없으면 비활성.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:8067"
    langfuse_enabled: bool = True

    @property
    def langfuse_is_enabled(self) -> bool:
        """키가 모두 존재하고 enabled일 때만 관측 활성 (ADR-0007)."""
        return self.langfuse_enabled and bool(self.langfuse_public_key) and bool(self.langfuse_secret_key)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
