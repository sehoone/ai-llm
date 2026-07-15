-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id         BIGSERIAL PRIMARY KEY,
    username   VARCHAR(100)  NOT NULL,
    email      VARCHAR(255)  NOT NULL UNIQUE,
    password   VARCHAR(255)  NOT NULL,
    role       VARCHAR(50)   NOT NULL DEFAULT 'USER',
    created_at TIMESTAMP     NOT NULL DEFAULT NOW()
);

-- 문서 임베딩 테이블 (text-embedding-3-small: 1536차원)
CREATE TABLE IF NOT EXISTS documents (
    id         BIGSERIAL PRIMARY KEY,
    title      VARCHAR(500)  NOT NULL,
    content    TEXT          NOT NULL,
    embedding  vector(1536),
    model      VARCHAR(100),
    created_at TIMESTAMP     NOT NULL DEFAULT NOW()
);

-- cosine 유사도 검색 인덱스 (HNSW: 데이터 없이 생성해도 동작, 높은 recall)
CREATE INDEX IF NOT EXISTS documents_embedding_idx
    ON documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
