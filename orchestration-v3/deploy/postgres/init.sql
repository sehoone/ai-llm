-- PostgreSQL 초기화 (볼륨이 비어있을 때 최초 1회 실행)
-- llmonl 스키마: V3 단일 backend가 소유 (ADR-0003)

CREATE SCHEMA IF NOT EXISTS llmonl;

-- pgvector 확장 (RAG 임베딩 — LLM 도메인 이식 시 사용)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ─────────────────────────────────────────────────────────────
-- 플랫폼 도메인 테이블 (V2 platform-server 포팅)
-- ⚠️ V2 대비 변경점 (ADR-0003):
--   - users: hashed_password 제거(비밀번호는 IdP 소유), idp_subject 추가(JIT 매핑 키)
--   - refresh_token 테이블 제거 (토큰 발급·갱신은 IdP 소유)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS llmonl.users (
    id           BIGSERIAL    PRIMARY KEY,
    idp_subject  VARCHAR(255) NOT NULL UNIQUE,   -- IdP 토큰 sub ↔ 로컬 id 매핑
    username     VARCHAR(255) NOT NULL UNIQUE,
    email        VARCHAR(255) NOT NULL UNIQUE,
    role         VARCHAR(50)  NOT NULL DEFAULT 'USER',
    status       VARCHAR(50)  NOT NULL DEFAULT 'active',
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_idp_subject ON llmonl.users (idp_subject);

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
-- 여기에 추가한다. 현재 V3는 플랫폼 도메인만 구현됨.
-- ─────────────────────────────────────────────────────────────
