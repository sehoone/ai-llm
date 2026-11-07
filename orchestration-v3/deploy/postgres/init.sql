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
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_session_user_id ON llmonl.chat_session (user_id);

CREATE TABLE IF NOT EXISTS llmonl.chat_message (
    id          BIGSERIAL    PRIMARY KEY,
    session_id  BIGINT       NOT NULL,
    role        VARCHAR(20)  NOT NULL,   -- user | assistant | tool
    content     TEXT         NOT NULL DEFAULT '',
    tool_calls  JSONB,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_message_session_id ON llmonl.chat_message (session_id);

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
