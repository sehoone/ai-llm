-- Keycloak 연동: users 테이블에 keycloak_id 컬럼 추가
-- Keycloak JWT의 sub (UUID 문자열)을 저장하여 로컬 사용자와 연결

ALTER TABLE llmonl.users
    ADD COLUMN IF NOT EXISTS keycloak_id VARCHAR(100) UNIQUE;

CREATE INDEX IF NOT EXISTS idx_users_keycloak_id ON llmonl.users (keycloak_id);
