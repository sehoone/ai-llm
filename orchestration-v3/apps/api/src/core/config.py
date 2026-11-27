import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# env 단일 소스는 deploy/environments/<env>/api.env (ADR-0018).
# bare-metal 개발(uv run poe dev)은 ENV_FILE로 그 파일을 가리킨다(poe dev가 주입).
# docker 배포는 compose가 env_file로 주입하므로 이 경로는 무시된다(파일 없음 → 기본값).
_ENV_FILE = os.environ.get("ENV_FILE", ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    app_env: str = "development"

    # 허용 Host 화이트리스트 (ADR-0032) — 콤마 구분. "*"면 전체 허용(로컬 기본).
    # 상용은 실제 호스트명으로 좁혀 Host 헤더 스푸핑을 차단한다. TrustedHostMiddleware가 사용.
    allowed_hosts: str = "*"

    # 로깅 (ADR-0031) — core/logging.configure_logging()이 사용. 레벨 DEBUG/INFO/WARNING/ERROR.
    log_level: str = "INFO"
    # 포맷: console(로컬 dev 기본, 사람이 읽는 평문) | json(docker/prd, Loki 필드 쿼리).
    log_format: str = "console"

    # PostgreSQL (schema: llmonl)
    # 127.0.0.1 명시(localhost 아님) — Windows에서 localhost는 IPv6 ::1을 먼저 시도하는데
    # docker 포트는 IPv4 127.0.0.1에만 바인딩되어, ::1 연결이 타임아웃까지 멈춘다(기동 지연/hang).
    postgres_host: str = "127.0.0.1"
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

    # 챗 유지보수 스윕 (ADR-0029) — 만료 승인 정리(+후속: 체크포인트 보존). 다중 인스턴스 안전(advisory lock).
    chat_maintenance_enabled: bool = True
    chat_maintenance_cron: str = "0 * * * *"  # 기본 매시 정각(UTC)

    # 워크플로우 엔진 (ADR-0019)
    workflow_scheduler_enabled: bool = True  # cron 스케줄(APScheduler) 기동 on/off
    workflow_http_timeout: int = 30          # http/loop 노드 기본 타임아웃(초)

    # 작업 큐 (ADR-0032 Phase 2) — Postgres SKIP LOCKED. meeting 등 장기작업을 API에서 분리.
    # worker_in_process: api 프로세스 안에서 워커 루프를 돌릴지(bare-metal/단일 인스턴스 기본 on).
    #   docker는 전용 worker 컨테이너를 쓰므로 compose가 api에 WORKER_IN_PROCESS=false override.
    worker_in_process: bool = True
    worker_poll_interval_seconds: int = 5          # 큐가 비었을 때 폴링 간격
    job_visibility_timeout_seconds: int = 1800     # running 작업 재큐잉 임계(크래시 복구, 30분)

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

    # 회의록 (meeting-minutes) — 음성 업로드·전사·요약. 오디오는 core/storage(MinIO/local)에
    # "meetings/" 네임스페이스로 저장. 요약 LLM은 llm_resource 기본 chat 리소스 사용(env 미참조).
    meeting_max_audio_mb: int = 200
    meeting_default_locale: str = "ko-KR"
    meeting_max_speakers: int = 10
    meeting_audio_bucket: str = "meeting-recordings"  # 녹음 전용 MinIO 버킷(첨부와 분리). local 백엔드면 무시.
    meeting_map_reduce_char_threshold: int = 12_000  # 초과 시 map-reduce 요약
    meeting_chunk_char_size: int = 8_000             # map 단계 청크 크기

    # 전사(STT) 외부 서비스 좌표 — llm_resource가 아님(별도 음성 서비스). Azure Fast Transcription
    # (주, 화자 분리) → OpenAI Whisper 폴백(화자 분리 없음). 둘 다 비면 전사 없이 오디오만 저장(SAVED).
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    openai_api_key: str = ""           # Whisper STT 폴백용
    openai_stt_model: str = "whisper-1"

    # 장기 메모리 (ADR-0015) — mem0 + pgvector. opt-in(추출 LLM 호출 비용·지연).
    # 추출 LLM·임베더 모델은 `llm_resource` 테이블에서 해석(env 미참조) — 도메인이 주입.
    memory_enabled: bool = False
    memory_collection: str = "longterm_memory"
    memory_max_count: int = 100
    # 임베딩 차원 — pgvector collection의 vector(N)·임베더 모델 출력 차원과 일치해야 한다(ADR-0015).
    # init.sql의 longterm_memory.vector(1536)와 동일 값을 유지. 모델 변경 시 함께 변경 + 볼륨 재생성.
    memory_embedder_dims: int = 1536
    postgres_schema: str = "llmonl"

    # Langfuse (LLM 관측 — ADR-0007). self-host 또는 cloud. 키 없으면 비활성.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://127.0.0.1:8067"  # localhost 아님 — Windows IPv6 ::1 stall 회피
    langfuse_enabled: bool = True

    @property
    def langfuse_is_enabled(self) -> bool:
        """키가 모두 존재하고 enabled일 때만 관측 활성 (ADR-0007)."""
        return self.langfuse_enabled and bool(self.langfuse_public_key) and bool(self.langfuse_secret_key)

    @property
    def allowed_hosts_list(self) -> list[str]:
        """콤마 구분 allowed_hosts를 리스트로 (TrustedHostMiddleware용)."""
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
