-- PostgreSQL 초기화 스크립트 (볼륨이 비어있을 때 최초 1회 실행)
-- llmonl 스키마: platform-server + orchestrator-server 공유

CREATE SCHEMA IF NOT EXISTS llmonl;

-- pgvector 확장 (RAG 임베딩 벡터 검색)
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────────────────────
-- platform-server 테이블 (JPA ddl-auto: validate)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS llmonl.users (
    id              BIGSERIAL    PRIMARY KEY,
    username        VARCHAR(255) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(50)  NOT NULL DEFAULT 'USER',
    status          VARCHAR(50)  NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP    NOT NULL,
    updated_at      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS llmonl.api_key (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    key         VARCHAR(255) NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL DEFAULT 'API Key',
    expires_at  TIMESTAMP,
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    created_at  TIMESTAMP    NOT NULL,
    updated_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS llmonl.refresh_token (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    token       VARCHAR(512) NOT NULL UNIQUE,
    expires_at  TIMESTAMP    NOT NULL,
    is_revoked  BOOLEAN      NOT NULL DEFAULT false,
    created_at  TIMESTAMP    NOT NULL,
    updated_at  TIMESTAMP
);

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
    created_at       TIMESTAMP    NOT NULL,
    updated_at       TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- orchestrator-server 테이블 (FastAPI / SQLModel)
-- ─────────────────────────────────────────────────────────────

-- 채팅 세션
CREATE TABLE IF NOT EXISTS llmonl.session (
    id         VARCHAR      PRIMARY KEY,
    user_id    INT          NOT NULL,
    name       VARCHAR      NOT NULL DEFAULT '',
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_session_user_id ON llmonl.session (user_id);

-- 채팅 메시지
CREATE TABLE IF NOT EXISTS llmonl.chat_message (
    id         BIGSERIAL    PRIMARY KEY,
    session_id VARCHAR      NOT NULL REFERENCES llmonl.session(id),
    question   TEXT         NOT NULL,
    answer     TEXT         NOT NULL,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_message_session_id ON llmonl.chat_message (session_id);

-- 채팅 첨부파일
CREATE TABLE IF NOT EXISTS llmonl.chat_attachment (
    id           BIGSERIAL    PRIMARY KEY,
    message_id   BIGINT       NOT NULL REFERENCES llmonl.chat_message(id),
    session_id   VARCHAR      NOT NULL,
    filename     VARCHAR      NOT NULL,
    content_type VARCHAR      NOT NULL,
    file_size    BIGINT       NOT NULL,
    storage_path VARCHAR      NOT NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_attachment_message_id ON llmonl.chat_attachment (message_id);
CREATE INDEX IF NOT EXISTS idx_chat_attachment_session_id ON llmonl.chat_attachment (session_id);

-- Custom GPT
CREATE TABLE IF NOT EXISTS llmonl.custom_gpt (
    id          VARCHAR      PRIMARY KEY,
    user_id     INT          NOT NULL,
    name        VARCHAR      NOT NULL,
    description TEXT,
    instructions TEXT        NOT NULL,
    rag_key     VARCHAR      NOT NULL,
    is_public   BOOLEAN      NOT NULL DEFAULT false,
    model       VARCHAR      NOT NULL DEFAULT 'gpt-4-turbo',
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_custom_gpt_user_id    ON llmonl.custom_gpt (user_id);
CREATE INDEX IF NOT EXISTS idx_custom_gpt_rag_key    ON llmonl.custom_gpt (rag_key);

-- Custom GPT 세션
CREATE TABLE IF NOT EXISTS llmonl.gpt_session (
    id            VARCHAR      PRIMARY KEY,
    user_id       INT          NOT NULL,
    custom_gpt_id VARCHAR      NOT NULL REFERENCES llmonl.custom_gpt(id),
    name          VARCHAR      NOT NULL DEFAULT '',
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gpt_session_user_id       ON llmonl.gpt_session (user_id);
CREATE INDEX IF NOT EXISTS idx_gpt_session_custom_gpt_id ON llmonl.gpt_session (custom_gpt_id);

-- Custom GPT 메시지
CREATE TABLE IF NOT EXISTS llmonl.gpt_chat_message (
    id         BIGSERIAL    PRIMARY KEY,
    session_id VARCHAR      NOT NULL REFERENCES llmonl.gpt_session(id),
    question   TEXT         NOT NULL,
    answer     TEXT         NOT NULL,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gpt_chat_message_session_id ON llmonl.gpt_chat_message (session_id);

-- Agent
CREATE TABLE IF NOT EXISTS llmonl.agent (
    id              VARCHAR      PRIMARY KEY,
    user_id         INT          NOT NULL,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    system_prompt   TEXT,
    welcome_message TEXT,
    model           VARCHAR      NOT NULL DEFAULT 'gpt-4o',
    temperature     FLOAT        NOT NULL DEFAULT 0.7,
    max_tokens      INT          NOT NULL DEFAULT 2000,
    rag_keys        TEXT[]       NOT NULL DEFAULT '{}',
    rag_groups      TEXT[]       NOT NULL DEFAULT '{}',
    rag_search_k    INT          NOT NULL DEFAULT 5,
    rag_enabled     BOOLEAN      NOT NULL DEFAULT false,
    tools_enabled   JSONB        NOT NULL DEFAULT '[]',
    allowed_models  TEXT[]       NOT NULL DEFAULT '{}',
    is_published    BOOLEAN      NOT NULL DEFAULT false,
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_user_id ON llmonl.agent (user_id);

-- Agent 세션
CREATE TABLE IF NOT EXISTS llmonl.agent_session (
    id         VARCHAR      PRIMARY KEY,
    agent_id   VARCHAR      NOT NULL,
    user_id    INT          NOT NULL,
    name       VARCHAR      NOT NULL DEFAULT '',
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_session_agent_id ON llmonl.agent_session (agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_session_user_id  ON llmonl.agent_session (user_id);

-- RAG 문서
CREATE TABLE IF NOT EXISTS llmonl.document (
    id           BIGSERIAL    PRIMARY KEY,
    user_id      INT,
    rag_key      VARCHAR      NOT NULL,
    rag_group    VARCHAR      NOT NULL,
    rag_type     VARCHAR      NOT NULL,
    filename     VARCHAR      NOT NULL,
    content      TEXT         NOT NULL,
    doc_metadata TEXT,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_document_user_id   ON llmonl.document (user_id);
CREATE INDEX IF NOT EXISTS idx_document_rag_key   ON llmonl.document (rag_key);
CREATE INDEX IF NOT EXISTS idx_document_rag_group ON llmonl.document (rag_group);
CREATE INDEX IF NOT EXISTS idx_document_rag_type  ON llmonl.document (rag_type);

-- RAG 임베딩 (pgvector)
CREATE TABLE IF NOT EXISTS llmonl.rag_embedding (
    id          BIGSERIAL    PRIMARY KEY,
    doc_id      BIGINT       NOT NULL REFERENCES llmonl.document(id) ON DELETE CASCADE,
    rag_key     VARCHAR      NOT NULL,
    rag_group   VARCHAR      NOT NULL,
    rag_type    VARCHAR      NOT NULL,
    chunk_index INT          NOT NULL,
    content     TEXT         NOT NULL,
    embedding   VECTOR(1536),
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_rag_key   ON llmonl.rag_embedding (rag_key);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_rag_group ON llmonl.rag_embedding (rag_group);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_doc_id    ON llmonl.rag_embedding (doc_id);

-- RAG 키 설정
CREATE TABLE IF NOT EXISTS llmonl.rag_key_config (
    id          VARCHAR      PRIMARY KEY,
    user_id     INT          NOT NULL,
    rag_key     VARCHAR      NOT NULL,
    rag_group   VARCHAR      NOT NULL,
    description TEXT,
    rag_type    VARCHAR      NOT NULL DEFAULT 'chatbot_shared',
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_rag_key_user UNIQUE (user_id, rag_key)
);
CREATE INDEX IF NOT EXISTS idx_rag_key_config_user_id  ON llmonl.rag_key_config (user_id);
CREATE INDEX IF NOT EXISTS idx_rag_key_config_rag_key  ON llmonl.rag_key_config (rag_key);
CREATE INDEX IF NOT EXISTS idx_rag_key_config_rag_group ON llmonl.rag_key_config (rag_group);

-- RAG 그룹 설정
CREATE TABLE IF NOT EXISTS llmonl.rag_group_config (
    id          VARCHAR      PRIMARY KEY,
    user_id     INT          NOT NULL,
    name        VARCHAR      NOT NULL,
    description TEXT,
    color       VARCHAR      NOT NULL DEFAULT '#6366f1',
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_rag_group_user_name UNIQUE (user_id, name)
);
CREATE INDEX IF NOT EXISTS idx_rag_group_config_user_id ON llmonl.rag_group_config (user_id);
CREATE INDEX IF NOT EXISTS idx_rag_group_config_name    ON llmonl.rag_group_config (name);

-- 워크플로우
CREATE TABLE IF NOT EXISTS llmonl.workflow (
    id            VARCHAR      PRIMARY KEY,
    user_id       INT          NOT NULL,
    name          VARCHAR(200) NOT NULL,
    description   TEXT         NOT NULL DEFAULT '',
    definition    JSONB        NOT NULL DEFAULT '{}',
    is_published  BOOLEAN      NOT NULL DEFAULT false,
    webhook_token VARCHAR,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_workflow_user_id       ON llmonl.workflow (user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_webhook_token ON llmonl.workflow (webhook_token);

-- 워크플로우 실행
CREATE TABLE IF NOT EXISTS llmonl.workflow_execution (
    id           VARCHAR      PRIMARY KEY,
    workflow_id  VARCHAR      NOT NULL,
    user_id      INT          NOT NULL,
    status       VARCHAR      NOT NULL DEFAULT 'pending',
    input_data   JSONB        NOT NULL DEFAULT '{}',
    output_data  JSONB,
    error        TEXT,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_workflow_execution_workflow_id ON llmonl.workflow_execution (workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_execution_user_id     ON llmonl.workflow_execution (user_id);

-- 워크플로우 노드 실행
CREATE TABLE IF NOT EXISTS llmonl.workflow_node_execution (
    id           VARCHAR      PRIMARY KEY,
    execution_id VARCHAR      NOT NULL,
    node_id      VARCHAR      NOT NULL,
    node_type    VARCHAR      NOT NULL,
    status       VARCHAR      NOT NULL DEFAULT 'pending',
    input_data   JSONB        NOT NULL DEFAULT '{}',
    output_data  JSONB,
    error        TEXT,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_workflow_node_execution_execution_id ON llmonl.workflow_node_execution (execution_id);

-- 워크플로우 스케줄
CREATE TABLE IF NOT EXISTS llmonl.workflow_schedule (
    id          VARCHAR      PRIMARY KEY,
    workflow_id VARCHAR      NOT NULL,
    user_id     INT          NOT NULL,
    label       VARCHAR(200) NOT NULL DEFAULT '',
    cron_expr   VARCHAR(100) NOT NULL,
    input_data  JSONB        NOT NULL DEFAULT '{}',
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    next_run_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_workflow_schedule_workflow_id ON llmonl.workflow_schedule (workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_schedule_user_id     ON llmonl.workflow_schedule (user_id);

-- 워크플로우 엔드포인트
CREATE TABLE IF NOT EXISTS llmonl.workflow_endpoint (
    id          VARCHAR      PRIMARY KEY,
    workflow_id VARCHAR      NOT NULL,
    user_id     INT          NOT NULL,
    path        VARCHAR(500) NOT NULL,
    method      VARCHAR(10)  NOT NULL DEFAULT 'POST',
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    description TEXT         NOT NULL DEFAULT '',
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_endpoint_path_method UNIQUE (path, method)
);
CREATE INDEX IF NOT EXISTS idx_workflow_endpoint_workflow_id ON llmonl.workflow_endpoint (workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_endpoint_user_id     ON llmonl.workflow_endpoint (user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_endpoint_path        ON llmonl.workflow_endpoint (path);

-- ─────────────────────────────────────────────────────────────
-- LangGraph PostgreSQL 체크포인터 테이블
-- (AsyncPostgresSaver가 search_path=llmonl,public으로 연결하므로
--  setup() 없이 사용하려면 여기서 미리 생성해야 함)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS llmonl.checkpoint_migrations (
    v INTEGER PRIMARY KEY
);

-- 노드별 전체 상태 스냅샷
CREATE TABLE IF NOT EXISTS llmonl.checkpoints (
    thread_id            TEXT NOT NULL,
    checkpoint_ns        TEXT NOT NULL DEFAULT '',
    checkpoint_id        TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type                 TEXT,
    checkpoint           JSONB NOT NULL,
    metadata             JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE INDEX IF NOT EXISTS checkpoints_thread_id_idx ON llmonl.checkpoints (thread_id);

-- 상태 직렬화 데이터 (채널 값 blob)
CREATE TABLE IF NOT EXISTS llmonl.checkpoint_blobs (
    thread_id     TEXT  NOT NULL,
    checkpoint_ns TEXT  NOT NULL DEFAULT '',
    channel       TEXT  NOT NULL,
    version       TEXT  NOT NULL,
    type          TEXT  NOT NULL,
    blob          BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
CREATE INDEX IF NOT EXISTS checkpoint_blobs_thread_id_idx ON llmonl.checkpoint_blobs (thread_id);

-- 노드 중간 쓰기 (내결함성용)
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
CREATE INDEX IF NOT EXISTS checkpoint_writes_thread_id_idx ON llmonl.checkpoint_writes (thread_id);
