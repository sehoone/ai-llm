-- ADR-0032 Phase 2: 작업 큐(job_queue) — Postgres SKIP LOCKED 기반 장기작업 큐.
-- 기존 postgres 볼륨(init.sql 재실행 안 됨)에 수동 적용용. 전부 멱등(IF NOT EXISTS).
--   docker exec -i orchestration-v3-stg-db-1 psql -U postgres -d mydb -v ON_ERROR_STOP=1 \
--     < deploy/postgres/migrations/0002_job_queue.sql

CREATE TABLE IF NOT EXISTS llmonl.job_queue (
    id            BIGSERIAL    PRIMARY KEY,
    job_type      VARCHAR(100) NOT NULL,
    payload       JSONB        NOT NULL DEFAULT '{}'::jsonb,
    status        VARCHAR(20)  NOT NULL DEFAULT 'queued',  -- queued|running|done|failed
    attempts      INT          NOT NULL DEFAULT 0,
    max_attempts  INT          NOT NULL DEFAULT 3,
    run_after     TIMESTAMP    NOT NULL DEFAULT NOW(),
    locked_at     TIMESTAMP,
    last_error    TEXT,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_job_queue_claim ON llmonl.job_queue (status, run_after);
