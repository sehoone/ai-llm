import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# env 단일 소스는 deploy/environments/<env>/api.env (ADR-0018).
# bare-metal 개발(uv run poe dev)은 ENV_FILE로 그 파일을 가리킨다(poe dev가 주입).
# docker 배포는 compose가 env_file로 주입하므로 이 경로는 무시된다(파일 없음 → 기본값).
_ENV_FILE = os.environ.get("ENV_FILE", ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

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

    # engine/llm — 실 LLM 호출 (ADR-0010). provider·model·key·endpoint는 전적으로 `llm_resource`
    # 테이블에서 온다(env 미참조). 아래는 테이블에 없는 생성 튜닝 기본값만 — 모델 선택과 무관.
    llm_temperature: float = 0.7
    llm_max_tokens: int = 0        # 0 = provider 기본값

    # 첨부 저장 (ADR-0017) — MinIO(S3 호환, 기본) 또는 로컬 디스크 폴백.
    # bare 로컬 개발(docker 없이)은 storage_backend=local로 두면 upload_dir에 저장.
    storage_backend: str = "minio"            # "minio" | "local"
    upload_dir: str = "uploads"               # local 폴백 저장 루트
    minio_endpoint: str = "minio:9000"        # 내부망 S3 엔드포인트 (host:port)
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "chat-attachments"    # Langfuse 버킷과 분리
    minio_secure: bool = False                # 내부 http

    # 문서 본문 추출 (ADR-0016) — 추출 텍스트 상한(컨텍스트 폭주 방지). 초과 시 truncate.
    max_extract_chars: int = 50_000

    # 장기 메모리 (ADR-0015) — mem0 + pgvector. opt-in(추출 LLM 호출 비용·지연).
    # 추출 LLM·임베더 모델은 `llm_resource` 테이블에서 해석(env 미참조) — 도메인이 주입.
    memory_enabled: bool = False
    memory_collection: str = "longterm_memory"
    memory_max_count: int = 100
    postgres_schema: str = "llmonl"

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
