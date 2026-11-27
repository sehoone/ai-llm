-- PostgreSQL 초기화 (볼륨이 비어있을 때 최초 1회 실행)
-- llmonl 스키마: V3 단일 backend가 소유 (ADR-0003)

CREATE SCHEMA IF NOT EXISTS llmonl;

-- pgvector 확장 (RAG 임베딩 — LLM 도메인 이식 시 사용)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ─────────────────────────────────────────────────────────────
-- 플랫폼 도메인 테이블 (V2 platform-server 포팅)
-- 인증: 백엔드가 ID/PW를 직접 검증하고 JWT(HS256)를 발급 (ADR-0003 전환).
--   - users.hashed_password: bcrypt 해시(자체 인증)
--   - users.idp_subject: 비활성·보존(OIDC 복귀용). 자체 인증에서는 NULL → nullable.
--   - refresh_token 테이블 없음 (만료 시 재로그인)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS llmonl.users (
    id               BIGSERIAL    PRIMARY KEY,
    username         VARCHAR(255) NOT NULL UNIQUE,
    email            VARCHAR(255) NOT NULL UNIQUE,
    hashed_password  VARCHAR(255),                  -- bcrypt (API 키 전용 사용자는 NULL)
    role             VARCHAR(50)  NOT NULL DEFAULT 'USER',
    status           VARCHAR(50)  NOT NULL DEFAULT 'active',
    idp_subject      VARCHAR(255) UNIQUE,            -- (보존) OIDC sub 매핑 — 자체 인증 시 NULL
    created_at       TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_idp_subject ON llmonl.users (idp_subject);

-- 기존 볼륨(OIDC 스키마로 생성됨) 마이그레이션 — 멱등.
ALTER TABLE llmonl.users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);
ALTER TABLE llmonl.users ALTER COLUMN idp_subject DROP NOT NULL;

CREATE TABLE IF NOT EXISTS llmonl.api_key (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    key         VARCHAR(255) NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL DEFAULT 'API Key',
    expires_at  TIMESTAMP,
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_api_key_user_id ON llmonl.api_key (user_id);

CREATE TABLE IF NOT EXISTS llmonl.llm_resource (
    id               BIGSERIAL    PRIMARY KEY,
    name             VARCHAR(255) NOT NULL,
    resource_type    VARCHAR(50)  NOT NULL DEFAULT 'chat',
    model_name       VARCHAR(255),
    provider         VARCHAR(255) NOT NULL,
    api_base         VARCHAR(255) NOT NULL,
    api_key          VARCHAR(255) NOT NULL,
    deployment_name  VARCHAR(255),
    api_version      VARCHAR(50),
    region           VARCHAR(100),
    priority         INT          NOT NULL DEFAULT 0,
    weight           INT          NOT NULL DEFAULT 1,
    is_active        BOOLEAN      NOT NULL DEFAULT true,
    created_at       TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- LLM 도메인 테이블 (chat·rag·agent·workflow·meeting)
-- 해당 도메인을 V2 orchestrator에서 포팅할 때 V2 deploy/postgres/init.sql의
-- orchestrator 섹션(session, document, rag_embedding, workflow*, meeting* 등)을
-- 여기에 추가한다.
-- ─────────────────────────────────────────────────────────────

-- chat 도메인 (ADR-0008): 대화 + 사용자 승인(HITL) 감사
CREATE TABLE IF NOT EXISTS llmonl.chat_session (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    title       VARCHAR(255) NOT NULL DEFAULT 'New chat',
    thread_rev  INTEGER      NOT NULL DEFAULT 0,   -- LangGraph 스레드 리비전 (재생성 포크, ADR-0020)
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_session_user_id ON llmonl.chat_session (user_id);
-- 기존 배포(테이블 이미 존재) 대응: 컬럼 멱등 추가.
ALTER TABLE llmonl.chat_session ADD COLUMN IF NOT EXISTS thread_rev INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS llmonl.chat_message (
    id          BIGSERIAL    PRIMARY KEY,
    session_id  BIGINT       NOT NULL,
    role        VARCHAR(20)  NOT NULL,   -- user | assistant | tool
    content     TEXT         NOT NULL DEFAULT '',
    tool_calls  JSONB,
    status      VARCHAR(20)  NOT NULL DEFAULT 'complete',  -- complete | aborted (중단 부분응답, ADR-0025 §5)
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_message_session_id ON llmonl.chat_message (session_id);
-- 기존 볼륨 멱등 ALTER (thread_rev와 동일 재실행-안전 패턴).
ALTER TABLE llmonl.chat_message ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'complete';

-- 승인 요청·결정 감사 (LangGraph 체크포인트와 분리 — 이력·재생방지·TTL·UI용)
CREATE TABLE IF NOT EXISTS llmonl.chat_approval (
    id            BIGSERIAL    PRIMARY KEY,
    session_id    BIGINT       NOT NULL,
    user_id       BIGINT       NOT NULL,
    group_key     VARCHAR(64)  NOT NULL,   -- 한 번의 interrupt로 묶인 요청 묶음
    tool_call_id  VARCHAR(255) NOT NULL,
    tool_name     VARCHAR(255) NOT NULL,
    args          JSONB        NOT NULL DEFAULT '{}'::jsonb,
    tier          VARCHAR(20)  NOT NULL DEFAULT 'CONFIRM',
    allow_edit    BOOLEAN      NOT NULL DEFAULT true,
    reason        TEXT,
    status        VARCHAR(20)  NOT NULL DEFAULT 'PENDING',  -- PENDING|APPROVED|REJECTED|EXPIRED
    decided_by    BIGINT,
    decided_at    TIMESTAMP,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_approval_session_id ON llmonl.chat_approval (session_id);
CREATE INDEX IF NOT EXISTS idx_chat_approval_group_key ON llmonl.chat_approval (group_key);

-- gpts 도메인 (V2 chatbot/custom_gpts 포팅): 사용자 정의 커스텀 GPT + 세션 + Q/A 이력.
-- FK 없음 — 연쇄 정리는 앱(repository)이 명시 수행(chat 도메인 관례와 동일).
CREATE TABLE IF NOT EXISTS llmonl.custom_gpt (
    id            TEXT         PRIMARY KEY,           -- uuid
    user_id       BIGINT       NOT NULL,
    name          VARCHAR(255) NOT NULL,
    description   VARCHAR(500),
    instructions  TEXT         NOT NULL DEFAULT '',
    rag_key       TEXT         NOT NULL,              -- GPT 전용 지식베이스 키
    is_public     BOOLEAN      NOT NULL DEFAULT false,
    model         VARCHAR(255) NOT NULL DEFAULT 'gpt-4o-mini',
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_custom_gpt_user_id ON llmonl.custom_gpt (user_id);
CREATE INDEX IF NOT EXISTS idx_custom_gpt_rag_key ON llmonl.custom_gpt (rag_key);

CREATE TABLE IF NOT EXISTS llmonl.gpt_session (
    id             TEXT        PRIMARY KEY,           -- uuid
    user_id        BIGINT      NOT NULL,
    custom_gpt_id  TEXT        NOT NULL,              -- custom_gpt.id
    name           VARCHAR(255) NOT NULL DEFAULT '',
    created_at     TIMESTAMP   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gpt_session_user_id ON llmonl.gpt_session (user_id);
CREATE INDEX IF NOT EXISTS idx_gpt_session_custom_gpt_id ON llmonl.gpt_session (custom_gpt_id);

CREATE TABLE IF NOT EXISTS llmonl.gpt_chat_message (
    id          BIGSERIAL   PRIMARY KEY,
    session_id  TEXT        NOT NULL,                 -- gpt_session.id
    question    TEXT        NOT NULL DEFAULT '',
    answer      TEXT        NOT NULL DEFAULT '',
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gpt_chat_message_session_id ON llmonl.gpt_chat_message (session_id);

-- rag 도메인 (ADR-0012): pgvector 임베딩 기반 검색 증강. 임베딩 차원 1536 고정.
CREATE TABLE IF NOT EXISTS llmonl.rag_group_config (
    id          TEXT         PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    name        TEXT         NOT NULL,
    description TEXT,
    color       TEXT         NOT NULL DEFAULT '#6366f1',
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP,
    CONSTRAINT uq_rag_group_user_name UNIQUE (user_id, name)
);
CREATE INDEX IF NOT EXISTS idx_rag_group_config_user_id ON llmonl.rag_group_config (user_id);

CREATE TABLE IF NOT EXISTS llmonl.rag_key_config (
    id          TEXT         PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    rag_key     TEXT         NOT NULL,
    rag_group   TEXT         NOT NULL,
    description TEXT,
    rag_type    TEXT         NOT NULL DEFAULT 'chatbot_shared',
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP,
    CONSTRAINT uq_rag_key_user UNIQUE (user_id, rag_key)
);
CREATE INDEX IF NOT EXISTS idx_rag_key_config_user_id ON llmonl.rag_key_config (user_id);
CREATE INDEX IF NOT EXISTS idx_rag_key_config_rag_group ON llmonl.rag_key_config (rag_group);

CREATE TABLE IF NOT EXISTS llmonl.document (
    id           BIGSERIAL   PRIMARY KEY,
    user_id      BIGINT,                 -- NULL = chatbot_shared
    rag_key      TEXT        NOT NULL,
    rag_group    TEXT        NOT NULL,
    rag_type     TEXT        NOT NULL,
    filename     TEXT        NOT NULL,
    content      TEXT        NOT NULL,
    doc_metadata TEXT,
    created_at   TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_document_rag_key ON llmonl.document (rag_key);
CREATE INDEX IF NOT EXISTS idx_document_rag_group ON llmonl.document (rag_group);
CREATE INDEX IF NOT EXISTS idx_document_user_id ON llmonl.document (user_id);

CREATE TABLE IF NOT EXISTS llmonl.rag_embedding (
    id          BIGSERIAL    PRIMARY KEY,
    doc_id      BIGINT       NOT NULL,
    rag_key     TEXT         NOT NULL,
    rag_group   TEXT         NOT NULL,
    rag_type    TEXT         NOT NULL,
    chunk_index INTEGER      NOT NULL,
    content     TEXT         NOT NULL,
    embedding   vector(1536),
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_doc_id ON llmonl.rag_embedding (doc_id);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_rag_group ON llmonl.rag_embedding (rag_group);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_rag_key ON llmonl.rag_embedding (rag_key);

-- artifact 도메인 (ADR-0013): 스트리밍 산출물 + 버전관리 + 공개 링크.
-- FK 없음 — 연쇄 정리는 앱(세션 삭제 → delete_session_artifacts; 아티팩트 삭제 → version/data 정리).
CREATE TABLE IF NOT EXISTS llmonl.artifact (
    id              TEXT         PRIMARY KEY,           -- uuid
    session_id      BIGINT       NOT NULL,              -- chat_session.id
    user_id         BIGINT       NOT NULL,
    identifier      TEXT         NOT NULL,              -- LLM이 준 식별자(세션 내 고유)
    artifact_type   TEXT         NOT NULL,
    title           TEXT         NOT NULL DEFAULT '',
    current_version INT          NOT NULL DEFAULT 1,
    is_published    BOOLEAN      NOT NULL DEFAULT false,
    public_token    TEXT,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_artifact_session_id   ON llmonl.artifact (session_id);
CREATE INDEX IF NOT EXISTS idx_artifact_user_id      ON llmonl.artifact (user_id);
CREATE INDEX IF NOT EXISTS idx_artifact_identifier   ON llmonl.artifact (identifier);
CREATE INDEX IF NOT EXISTS idx_artifact_public_token ON llmonl.artifact (public_token);

CREATE TABLE IF NOT EXISTS llmonl.artifact_version (
    id          BIGSERIAL    PRIMARY KEY,
    artifact_id TEXT         NOT NULL,
    version     INT          NOT NULL,
    content     TEXT         NOT NULL,
    message_id  BIGINT,                                 -- chat_message.id
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_artifact_version_artifact_id ON llmonl.artifact_version (artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifact_version_message_id  ON llmonl.artifact_version (message_id);

CREATE TABLE IF NOT EXISTS llmonl.artifact_data (
    artifact_id TEXT      PRIMARY KEY,
    data        TEXT      NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- chat 첨부 (ADR-0014): 파일 바이트는 로컬 볼륨, 메타만 DB. FK 없음 — 앱이 정리.
CREATE TABLE IF NOT EXISTS llmonl.chat_attachment (
    id           BIGSERIAL  PRIMARY KEY,
    message_id   BIGINT     NOT NULL,
    session_id   BIGINT     NOT NULL,
    filename     TEXT       NOT NULL,
    content_type TEXT       NOT NULL,
    file_size    BIGINT     NOT NULL,
    storage_path TEXT       NOT NULL,
    created_at   TIMESTAMP  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_attachment_message_id ON llmonl.chat_attachment (message_id);
CREATE INDEX IF NOT EXISTS idx_chat_attachment_session_id ON llmonl.chat_attachment (session_id);

-- meeting 도메인: 음성 회의록(업로드·전사·요약). 오디오 바이트는 객체 스토리지(core/storage),
-- 메타·전사·회의록만 DB. FK CASCADE 없음 — 회의 삭제 시 앱이 세그먼트·회의록·아티팩트를 정리.
CREATE TABLE IF NOT EXISTS llmonl.meeting (
    id                      TEXT         PRIMARY KEY,           -- uuid(hex)
    user_id                 BIGINT       NOT NULL,
    title                   TEXT         NOT NULL DEFAULT '',
    status                  VARCHAR(20)  NOT NULL DEFAULT 'UPLOADED',  -- UPLOADED|TRANSCRIBING|TRANSCRIBED|SUMMARIZING|COMPLETED|SAVED|FAILED
    audio_object_key        TEXT         NOT NULL,
    audio_filename          TEXT         NOT NULL DEFAULT '',
    audio_duration_sec      INTEGER,
    language                VARCHAR(20)  NOT NULL DEFAULT 'ko-KR',
    transcription_provider  VARCHAR(20),                        -- azure|whisper
    artifact_id             TEXT,
    public_token            TEXT,
    error_message           TEXT,
    created_at              TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meeting_user_id      ON llmonl.meeting (user_id);
CREATE INDEX IF NOT EXISTS idx_meeting_status       ON llmonl.meeting (status);
CREATE INDEX IF NOT EXISTS idx_meeting_artifact_id  ON llmonl.meeting (artifact_id);
CREATE INDEX IF NOT EXISTS idx_meeting_public_token ON llmonl.meeting (public_token);

CREATE TABLE IF NOT EXISTS llmonl.meeting_segment (
    id            BIGSERIAL    PRIMARY KEY,
    meeting_id    TEXT         NOT NULL,
    seq           INTEGER      NOT NULL,
    speaker_label VARCHAR(50)  NOT NULL DEFAULT 'Speaker 1',  -- 공급자 할당 라벨
    speaker_name  VARCHAR(255),                               -- 사용자 매핑 실명
    start_ms      INTEGER      NOT NULL DEFAULT 0,
    end_ms        INTEGER      NOT NULL DEFAULT 0,
    text          TEXT         NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_meeting_segment_meeting_id ON llmonl.meeting_segment (meeting_id);

CREATE TABLE IF NOT EXISTS llmonl.meeting_minutes (
    id           BIGSERIAL   PRIMARY KEY,
    meeting_id   TEXT        NOT NULL,
    summary      TEXT        NOT NULL DEFAULT '',
    content_json TEXT        NOT NULL DEFAULT '{}',   -- 구조화 회의록(JSON 인코딩)
    model_used   VARCHAR(255) NOT NULL DEFAULT '',
    version      INT         NOT NULL DEFAULT 1,
    created_at   TIMESTAMP   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meeting_minutes_meeting_id ON llmonl.meeting_minutes (meeting_id);

-- ─────────────────────────────────────────────────────────────
-- workflow 도메인 (ADR-0019): 노드 그래프 DAG 실행 엔진.
-- definition은 React Flow {nodes,edges} JSON. FK CASCADE 없음 — 앱(repository)이 연쇄 정리.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS llmonl.workflow (
    id            TEXT         PRIMARY KEY,
    user_id       BIGINT       NOT NULL,
    name          VARCHAR(200) NOT NULL,
    description   TEXT         NOT NULL DEFAULT '',
    definition    JSONB        NOT NULL DEFAULT '{}'::jsonb,  -- {nodes:[...], edges:[...]}
    is_published  BOOLEAN      NOT NULL DEFAULT false,
    webhook_token TEXT,                                       -- NULL = 웹훅 비활성
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_workflow_user_id       ON llmonl.workflow (user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_webhook_token ON llmonl.workflow (webhook_token);

CREATE TABLE IF NOT EXISTS llmonl.workflow_execution (
    id           TEXT        PRIMARY KEY,
    workflow_id  TEXT        NOT NULL,
    user_id      BIGINT      NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending|running|completed|failed|skipped
    input_data   JSONB       NOT NULL DEFAULT '{}'::jsonb,
    output_data  JSONB,
    error        TEXT,
    created_at   TIMESTAMP   NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_workflow_execution_workflow_id ON llmonl.workflow_execution (workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_execution_user_id     ON llmonl.workflow_execution (user_id);

CREATE TABLE IF NOT EXISTS llmonl.workflow_node_execution (
    id           TEXT        PRIMARY KEY,
    execution_id TEXT        NOT NULL,
    node_id      TEXT        NOT NULL,   -- 프론트 캔버스 node id
    node_type    TEXT        NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'pending',
    input_data   JSONB       NOT NULL DEFAULT '{}'::jsonb,
    output_data  JSONB,
    error        TEXT,
    created_at   TIMESTAMP   NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_workflow_node_execution_execution_id ON llmonl.workflow_node_execution (execution_id);

CREATE TABLE IF NOT EXISTS llmonl.workflow_schedule (
    id           TEXT         PRIMARY KEY,   -- APScheduler job_id
    workflow_id  TEXT         NOT NULL,
    user_id      BIGINT       NOT NULL,
    label        VARCHAR(200) NOT NULL DEFAULT '',
    cron_expr    VARCHAR(100) NOT NULL,
    input_data   JSONB        NOT NULL DEFAULT '{}'::jsonb,
    is_active    BOOLEAN      NOT NULL DEFAULT true,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    next_run_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_workflow_schedule_workflow_id ON llmonl.workflow_schedule (workflow_id);

CREATE TABLE IF NOT EXISTS llmonl.workflow_endpoint (
    id           TEXT         PRIMARY KEY,
    workflow_id  TEXT         NOT NULL,
    user_id      BIGINT       NOT NULL,
    path         VARCHAR(500) NOT NULL,   -- /api/v1/run/ 뒤 접미사
    method       VARCHAR(10)  NOT NULL DEFAULT 'POST',
    is_active    BOOLEAN      NOT NULL DEFAULT true,
    description  TEXT         NOT NULL DEFAULT '',
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_endpoint_path_method UNIQUE (path, method)
);
CREATE INDEX IF NOT EXISTS idx_workflow_endpoint_workflow_id ON llmonl.workflow_endpoint (workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_endpoint_path        ON llmonl.workflow_endpoint (path);

-- ─────────────────────────────────────────────────────────────
-- project 도메인 (ADR-0021): 대화·지침·지식을 묶는 작업공간.
-- 대화는 chat 스택 재사용(chat_session.project_id), 지식은 rag 전용 그룹 재사용.
-- FK CASCADE 없음 — 프로젝트 삭제 시 앱(repository)이 세션·지식 연쇄 정리.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS llmonl.project (
    id            TEXT         PRIMARY KEY,                 -- uuid
    user_id       BIGINT       NOT NULL,
    name          TEXT         NOT NULL,
    description   TEXT,
    instructions  TEXT         NOT NULL DEFAULT '',         -- 공유 system prompt
    rag_key       TEXT         NOT NULL,                    -- 전용 지식베이스 키
    rag_group     TEXT         NOT NULL,                    -- rag_group_config.name (1:1)
    icon          TEXT         NOT NULL DEFAULT 'folder',
    color         TEXT         NOT NULL DEFAULT '#6366f1',
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_project_user_id ON llmonl.project (user_id);

-- chat_session에 소속 프로젝트 연결 (thread_rev와 동일한 재실행-안전 ALTER 패턴).
ALTER TABLE llmonl.chat_session ADD COLUMN IF NOT EXISTS project_id TEXT;  -- NULL = 일반 대화
CREATE INDEX IF NOT EXISTS idx_chat_session_project_id ON llmonl.chat_session (project_id);

-- ─────────────────────────────────────────────────────────────
-- connector 도메인 (ADR-0022): 챗 도구를 사내 MCP 서버로 확장.
-- 등록·인가는 domain, 도구 로드·위험도는 engine/agent. sk- 키는 참조로만 보관.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS llmonl.connector (
    id             TEXT         PRIMARY KEY,                -- uuid
    user_id        BIGINT       NOT NULL,
    name           TEXT         NOT NULL,
    description    TEXT,
    mcp_url        TEXT         NOT NULL,                   -- spring-ai-mcp /mcp 좌표
    credential_ref TEXT,                                    -- sk- 키 참조(평문 금지)
    enabled        BOOLEAN      NOT NULL DEFAULT true,
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_connector_user_id ON llmonl.connector (user_id);

-- ─────────────────────────────────────────────────────────────
-- skill 도메인 (ADR-0024): 재사용 지침 프리셋. body를 system prompt에 합성.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS llmonl.skill (
    id           TEXT         PRIMARY KEY,                  -- uuid
    user_id      BIGINT       NOT NULL,
    name         TEXT         NOT NULL,
    description  TEXT,
    body         TEXT         NOT NULL DEFAULT '',          -- 지침 본문
    icon         TEXT         NOT NULL DEFAULT 'sparkles',
    color        TEXT         NOT NULL DEFAULT '#6366f1',
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_skill_user_id ON llmonl.skill (user_id);

-- project ↔ skill 기본 활성 스킬 (ADR-0024 §4 · ADR-0021): 프로젝트 대화에 자동 적용.
-- FK 없음(도메인 관례) — 연쇄 정리는 앱이 수행. sort_order로 합성 순서(우선순위)를 보존.
CREATE TABLE IF NOT EXISTS llmonl.project_skill (
    project_id  TEXT     NOT NULL,
    skill_id    TEXT     NOT NULL,
    sort_order  INT      NOT NULL DEFAULT 0,
    PRIMARY KEY (project_id, skill_id)
);
CREATE INDEX IF NOT EXISTS idx_project_skill_project ON llmonl.project_skill (project_id);

-- ─────────────────────────────────────────────────────────────
-- LangGraph 체크포인터 (ADR-0028): HITL 승인·되묻기·중단 세션의 재개 상태 저장소.
-- 스키마는 langgraph-checkpoint-postgres가 소유하나, 본 프로젝트는 **DDL을 init.sql로만 관리**한다
-- (AsyncPostgresSaver.setup() 런타임 DDL 미사용 — ADR-0028 개정). 아래는 v3.2.1 런타임이 쓰는 테이블.
-- 개발 단계 정책: **migration 버전 관리 없음**(checkpoint_migrations·seed 제외). 런타임(aput/aget/alist/
-- adelete)은 아래 3개 테이블만 쓰고 checkpoint_migrations는 setup() 전용이라 불요. 스키마가 바뀌면
-- (langgraph 업그레이드 등) **DB 볼륨을 재생성**한다(task deploy-down ENV=<e> → 재배포). 즉 "지우고 다시 생성".
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS llmonl.checkpoints (
    thread_id            TEXT  NOT NULL,
    checkpoint_ns        TEXT  NOT NULL DEFAULT '',
    checkpoint_id        TEXT  NOT NULL,
    parent_checkpoint_id TEXT,
    type                 TEXT,
    checkpoint           JSONB NOT NULL,
    metadata             JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE INDEX IF NOT EXISTS checkpoints_thread_id_idx ON llmonl.checkpoints USING btree (thread_id);
CREATE TABLE IF NOT EXISTS llmonl.checkpoint_blobs (
    thread_id     TEXT  NOT NULL,
    checkpoint_ns TEXT  NOT NULL DEFAULT '',
    channel       TEXT  NOT NULL,
    version       TEXT  NOT NULL,
    type          TEXT  NOT NULL,
    blob          BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
CREATE INDEX IF NOT EXISTS checkpoint_blobs_thread_id_idx ON llmonl.checkpoint_blobs USING btree (thread_id);
CREATE TABLE IF NOT EXISTS llmonl.checkpoint_writes (
    thread_id     TEXT    NOT NULL,
    checkpoint_ns TEXT    NOT NULL DEFAULT '',
    checkpoint_id TEXT    NOT NULL,
    task_id       TEXT    NOT NULL,
    idx           INTEGER NOT NULL,
    channel       TEXT    NOT NULL,
    type          TEXT,
    blob          BYTEA   NOT NULL,
    task_path     TEXT    NOT NULL DEFAULT '',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
CREATE INDEX IF NOT EXISTS checkpoint_writes_thread_id_idx ON llmonl.checkpoint_writes USING btree (thread_id);

-- ─────────────────────────────────────────────────────────────
-- 장기 메모리 collection (ADR-0015): mem0 pgvector 벡터 스토어.
-- mem0는 테이블이 **없을 때만** create_col()을 실행하므로(_ensure_collection: list_cols 확인 후 skip),
-- 여기서 **선재 생성**하면 앱(mem0)은 DDL을 전혀 실행하지 않는다(ADR-0028 "앱 테이블 생성 금지" 정책 일관).
-- 스키마·인덱스명은 mem0 create_col과 동일하게 맞춘다(hnsw=기본 on, diskann=off).
-- ⚠️ vector(1536)의 차원은 **임베더 모델 출력 차원**과 일치해야 한다 — `MEMORY_EMBEDDER_DIMS`(기본 1536 =
--    text-embedding-3-small)와 동일 값. 임베더를 다른 차원 모델로 바꾸면 이 숫자도 바꾸고 볼륨을 재생성한다.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS llmonl.longterm_memory (
    id      UUID         PRIMARY KEY,
    vector  vector(1536),
    payload JSONB
);
CREATE INDEX IF NOT EXISTS longterm_memory_hnsw_idx
    ON llmonl.longterm_memory USING hnsw (vector vector_cosine_ops);
CREATE INDEX IF NOT EXISTS longterm_memory_text_lemmatized_idx
    ON llmonl.longterm_memory USING gin (to_tsvector('simple', payload->>'text_lemmatized'));

-- ─────────────────────────────────────────────────────────────
-- 작업 큐 (ADR-0032 Phase 2) — Postgres SELECT … FOR UPDATE SKIP LOCKED 기반.
-- meeting 전사·요약 등 장기 작업을 API 프로세스에서 분리(재시작 내구·재시도·레플리카 분산).
-- status: queued|running|done|failed. 크래시 복구는 visibility timeout(locked_at)으로 재큐잉.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS llmonl.job_queue (
    id            BIGSERIAL    PRIMARY KEY,
    job_type      VARCHAR(100) NOT NULL,
    payload       JSONB        NOT NULL DEFAULT '{}'::jsonb,
    status        VARCHAR(20)  NOT NULL DEFAULT 'queued',
    attempts      INT          NOT NULL DEFAULT 0,
    max_attempts  INT          NOT NULL DEFAULT 3,
    run_after     TIMESTAMP    NOT NULL DEFAULT NOW(),
    locked_at     TIMESTAMP,
    last_error    TEXT,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);
-- 클레임 조회(status='queued' AND run_after<=now, id 순) + 재큐잉 스캔(status='running')용.
CREATE INDEX IF NOT EXISTS idx_job_queue_claim ON llmonl.job_queue (status, run_after);

-- ─────────────────────────────────────────────────────────────
-- 폐기 토큰 블랙리스트 (ADR-0032 Phase 2) — 로그아웃 시 JWT jti를 등록해 만료 전 무효화.
-- get_current_user가 jti 조회로 차단. 만료분은 유지보수 스윕이 삭제(테이블 증가 방지).
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS llmonl.revoked_token (
    jti        VARCHAR(64) PRIMARY KEY,
    user_id    BIGINT      NOT NULL,
    expires_at TIMESTAMP   NOT NULL,
    revoked_at TIMESTAMP   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_revoked_token_expires ON llmonl.revoked_token (expires_at);
