-- ============================================================
-- poc-vector-search DB 초기화 스크립트
-- PostgreSQL 컨테이너 최초 기동 시 /docker-entrypoint-initdb.d/ 에 의해 자동 실행됨
-- (볼륨이 비어있을 때만 실행 — 재기동 시 재실행되지 않음)
-- ============================================================

-- ── pgvector 확장 ────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;

-- ── 사용자 테이블 ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         BIGSERIAL    PRIMARY KEY,
    username   VARCHAR(100) NOT NULL,
    email      VARCHAR(255) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,               -- BCrypt 해시
    role       VARCHAR(50)  NOT NULL DEFAULT 'USER', -- USER | ADMIN
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── 문서 임베딩 테이블 ───────────────────────────────────────
-- embedding 차원: text-embedding-3-small = 1536
-- 모델 변경 시 embedding 컬럼의 차원(1536)도 함께 수정 필요
CREATE TABLE IF NOT EXISTS documents (
    id         BIGSERIAL    PRIMARY KEY,
    title      VARCHAR(500) NOT NULL,
    content    TEXT         NOT NULL,
    embedding  vector(1536),
    model      VARCHAR(100),
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── 벡터 검색 인덱스 (cosine 유사도) ────────────────────────
-- IVFFlat: 대용량 데이터에 적합한 근사 최근접 이웃 인덱스
-- lists 값은 저장 문서 수의 제곱근 수준으로 조정 권장 (100~1000)
CREATE INDEX IF NOT EXISTS documents_embedding_idx
    ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ── 초기 데이터 ──────────────────────────────────────────────
-- admin 계정: admin@poc.com / admin1234 (BCrypt $2a$10$...)
INSERT INTO users (username, email, password, role)
SELECT 'admin',
       'admin@poc.com',
       '$2b$10$3apYfhkAj8ahXoBT8iuGI.x1DAmbKNDucWzBup9bXEVgw.KVSsEly',
       'ADMIN'
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'admin@poc.com'
);
