-- ============================================================
-- Init Seed Data  (멱등, 중복 실행 안전)
--
-- 실행 방법:
--   docker exec -i db psql -U <POSTGRES_USER> -d <POSTGRES_DB> \
--     < deploy/postgres/seed.sql
--
-- 기본 계정 비밀번호
--   superadmin / admin  →  admin1234!
--   user1               →  user1234!
--
-- !! LLM 리소스의 api_key 는 실제 키로 교체 후 실행 !!
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- Users
-- ─────────────────────────────────────────────────────────────
INSERT INTO llmonl.users
    (username, email, hashed_password, role, status, created_at, updated_at)
VALUES
    (
        'superadmin',
        'superadmin@example.com',
        '$2b$10$y7axedjBPt9Gp1eWDcp2E.ET9.G0ZUldvj6tWlJ8iSu4dyEjsNI46',
        'SUPERADMIN', 'active', NOW(), NOW()
    ),
    (
        'admin',
        'admin@example.com',
        '$2b$10$y7axedjBPt9Gp1eWDcp2E.ET9.G0ZUldvj6tWlJ8iSu4dyEjsNI46',
        'ADMIN', 'active', NOW(), NOW()
    ),
    (
        'user1',
        'user1@example.com',
        '$2b$10$.cd3ASAgKaZf/lNQiH.jl.qaJaiXpn4zkRoROOEni1p.ZQD3.rbv6',
        'USER', 'active', NOW(), NOW()
    )
ON CONFLICT (username) DO NOTHING;

-- ─────────────────────────────────────────────────────────────
-- LLM Resources
-- ─────────────────────────────────────────────────────────────
-- name 에 unique constraint 가 없으므로 EXISTS 체크로 멱등 보장
INSERT INTO llmonl.llm_resource
    (name, resource_type, model_name, provider,
     api_base, api_key,
     deployment_name, api_version, region,
     priority, weight, is_active, created_at, updated_at)
SELECT
    'GPT-4o', 'chat', 'gpt-4o', 'openai',
    'https://api.openai.com/v1', 'REPLACE_WITH_OPENAI_API_KEY',
    NULL, NULL, NULL,
    10, 1, true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM llmonl.llm_resource WHERE name = 'GPT-4o');

INSERT INTO llmonl.llm_resource
    (name, resource_type, model_name, provider,
     api_base, api_key,
     deployment_name, api_version, region,
     priority, weight, is_active, created_at, updated_at)
SELECT
    'GPT-4o-mini', 'chat', 'gpt-4o-mini', 'openai',
    'https://api.openai.com/v1', 'REPLACE_WITH_OPENAI_API_KEY',
    NULL, NULL, NULL,
    5, 2, true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM llmonl.llm_resource WHERE name = 'GPT-4o-mini');

INSERT INTO llmonl.llm_resource
    (name, resource_type, model_name, provider,
     api_base, api_key,
     deployment_name, api_version, region,
     priority, weight, is_active, created_at, updated_at)
SELECT
    'text-embedding-3-small', 'embedding', 'text-embedding-3-small', 'openai',
    'https://api.openai.com/v1', 'REPLACE_WITH_OPENAI_API_KEY',
    NULL, NULL, NULL,
    10, 1, true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM llmonl.llm_resource WHERE name = 'text-embedding-3-small');

-- ─────────────────────────────────────────────────────────────
-- 결과 확인
-- ─────────────────────────────────────────────────────────────
SELECT id, username, email, role, status FROM llmonl.users ORDER BY id;
SELECT id, name, resource_type, model_name, provider, priority, weight, is_active FROM llmonl.llm_resource ORDER BY resource_type, priority DESC;
