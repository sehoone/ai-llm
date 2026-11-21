-- ADR-0021/0022/0024: project·skill·connector 테이블 + chat_session.project_id.
-- 기존 postgres 볼륨(init.sql 재실행 안 됨)에 수동 적용용. 전부 멱등(IF NOT EXISTS).
--   docker exec -i orchestration-v3-stg-db-1 psql -U postgres -d mydb -v ON_ERROR_STOP=1 \
--     < deploy/postgres/migrations/0001_projects_skills_connectors.sql

CREATE TABLE IF NOT EXISTS llmonl.project (
    id            TEXT         PRIMARY KEY,
    user_id       BIGINT       NOT NULL,
    name          TEXT         NOT NULL,
    description   TEXT,
    instructions  TEXT         NOT NULL DEFAULT '',
    rag_key       TEXT         NOT NULL,
    rag_group     TEXT         NOT NULL,
    icon          TEXT         NOT NULL DEFAULT 'folder',
    color         TEXT         NOT NULL DEFAULT '#6366f1',
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_project_user_id ON llmonl.project (user_id);

ALTER TABLE llmonl.chat_session ADD COLUMN IF NOT EXISTS project_id TEXT;
CREATE INDEX IF NOT EXISTS idx_chat_session_project_id ON llmonl.chat_session (project_id);

CREATE TABLE IF NOT EXISTS llmonl.connector (
    id             TEXT         PRIMARY KEY,
    user_id        BIGINT       NOT NULL,
    name           TEXT         NOT NULL,
    description    TEXT,
    mcp_url        TEXT         NOT NULL,
    credential_ref TEXT,
    enabled        BOOLEAN      NOT NULL DEFAULT true,
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_connector_user_id ON llmonl.connector (user_id);

CREATE TABLE IF NOT EXISTS llmonl.skill (
    id           TEXT         PRIMARY KEY,
    user_id      BIGINT       NOT NULL,
    name         TEXT         NOT NULL,
    description  TEXT,
    body         TEXT         NOT NULL DEFAULT '',
    icon         TEXT         NOT NULL DEFAULT 'sparkles',
    color        TEXT         NOT NULL DEFAULT '#6366f1',
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_skill_user_id ON llmonl.skill (user_id);
