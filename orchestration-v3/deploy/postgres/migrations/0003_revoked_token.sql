-- ADR-0032 Phase 2: JWT 폐기 블랙리스트(revoked_token) — 로그아웃 시 jti 등록.
-- 기존 postgres 볼륨(init.sql 재실행 안 됨)에 수동 적용용. 전부 멱등(IF NOT EXISTS).
--   docker exec -i orchestration-v3-stg-db-1 psql -U postgres -d mydb -v ON_ERROR_STOP=1 \
--     < deploy/postgres/migrations/0003_revoked_token.sql

CREATE TABLE IF NOT EXISTS llmonl.revoked_token (
    jti        VARCHAR(64) PRIMARY KEY,
    user_id    BIGINT      NOT NULL,
    expires_at TIMESTAMP   NOT NULL,
    revoked_at TIMESTAMP   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_revoked_token_expires ON llmonl.revoked_token (expires_at);
