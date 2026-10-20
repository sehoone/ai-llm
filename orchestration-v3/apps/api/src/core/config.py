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

    # 사내 IdP (OIDC) — 인증 위임, 백엔드는 토큰 검증만 (ADR-0003)
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    # role 권위는 IdP 클레임. 토큰에서 역할을 읽을 클레임 경로(단일 문자열 또는 문자열 배열 허용).
    oidc_role_claim: str = "roles"
    # 토큰 식별 클레임 → 로컬 user 프로비저닝에 사용
    oidc_username_claim: str = "preferred_username"
    oidc_email_claim: str = "email"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
