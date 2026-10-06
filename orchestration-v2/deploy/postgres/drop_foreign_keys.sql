-- ─────────────────────────────────────────────────────────────
-- 기존 운영 DB에서 외래키(FK) 제약을 제거하는 마이그레이션.
--
-- 배경: FK(ON DELETE CASCADE 포함)를 더 이상 사용하지 않기로 함.
--   - 신규 DB: init.sql / SQLModel 모델에서 이미 FK가 제거됨.
--   - 기존 DB: 테이블 생성 시점에 걸린 제약이 그대로 남아 있으므로
--     이 스크립트로 직접 DROP 해야 함.
--
-- FK 제약 이름은 생성 경로(init.sql vs SQLModel)에 따라 다를 수 있어
-- (예: chat_message_session_id_fkey), 대상 테이블의 FK를 동적으로
-- 조회해서 모두 DROP 한다. 멱등(idempotent) — 이미 없으면 아무 일도 안 함.
--
-- 실행:
--   docker exec -i orchestration-db psql -U postgres -d mydb < drop_foreign_keys.sql
-- 또는 psql로 직접:
--   psql -h <host> -p <port> -U postgres -d mydb -f drop_foreign_keys.sql
-- ─────────────────────────────────────────────────────────────

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT con.conname, nsp.nspname, rel.relname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
        WHERE con.contype = 'f'
          AND nsp.nspname = 'llmonl'
          AND rel.relname IN (
              'chat_message',
              'chat_attachment',
              'gpt_session',
              'gpt_chat_message',
              'rag_embedding',
              'ai_overview_keyword',
              'artifact',
              'artifact_version',
              'artifact_data',
              'agent_session'
          )
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I',
            r.nspname, r.relname, r.conname
        );
        RAISE NOTICE 'Dropped FK % on %.%', r.conname, r.nspname, r.relname;
    END LOOP;
END $$;
