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

-- 원본 문서 (소스 관리 및 인덱싱 상태 추적)
-- status: pending | processing | indexed | failed
CREATE TABLE IF NOT EXISTS documents (
    id            BIGSERIAL    PRIMARY KEY,
    title         VARCHAR(500) NOT NULL,
    full_content  TEXT         NOT NULL,
    source_type   VARCHAR(50)  NOT NULL DEFAULT 'manual',
    status        VARCHAR(20)  NOT NULL DEFAULT 'pending',
    model         VARCHAR(100),
    error_message TEXT,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- 청크 + 벡터 (검색 대상, documents 삭제 시 CASCADE)
CREATE TABLE IF NOT EXISTS document_chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  BIGINT    NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index  INTEGER   NOT NULL,
    chunk_total  INTEGER   NOT NULL,
    content      TEXT      NOT NULL,
    embedding    vector(1536),
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

-- 벡터 검색 인덱스 (document_chunks)
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx
    ON document_chunks (document_id);
