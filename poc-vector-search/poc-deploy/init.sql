-- ============================================================
-- poc-vector-search DB 초기화 스크립트
-- PostgreSQL 컨테이너 최초 기동 시 /docker-entrypoint-initdb.d/ 에 의해 자동 실행됨
-- (볼륨이 비어있을 때만 실행 — 재기동 시 재실행되지 않음)
-- ============================================================


-- ══════════════════════════════════════════════════════════════
-- [1] pgvector 확장
-- ══════════════════════════════════════════════════════════════
--
-- pgvector란?
--   PostgreSQL에 "벡터 데이터 타입"과 "벡터 유사도 검색"을 추가하는 공식 확장.
--   텍스트·이미지·오디오를 AI 모델로 숫자 배열(임베딩)로 바꾼 뒤,
--   "의미가 비슷한 것"을 빠르게 찾아주는 것이 핵심 역할이다.
--
-- 왜 필요한가?
--   일반 SQL의 WHERE/LIKE는 문자가 정확히 일치할 때만 동작한다.
--   "강아지"와 "개"처럼 표현은 달라도 의미가 같은 경우를 찾으려면
--   벡터 간 거리(유사도)를 계산해야 하고, pgvector가 그 기능을 제공한다.
--
CREATE EXTENSION IF NOT EXISTS vector;


-- ══════════════════════════════════════════════════════════════
-- [2] 사용자 테이블
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id         BIGSERIAL    PRIMARY KEY,
    username   VARCHAR(100) NOT NULL,
    email      VARCHAR(255) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,                -- BCrypt 해시
    role       VARCHAR(50)  NOT NULL DEFAULT 'USER', -- USER | ADMIN
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);


-- ══════════════════════════════════════════════════════════════
-- [3] 문서 임베딩 테이블
-- ══════════════════════════════════════════════════════════════
--
-- ── 임베딩(Embedding)이란? ───────────────────────────────────
--   텍스트를 AI 모델(여기서는 Azure OpenAI text-embedding-3-small)이
--   숫자 배열(float[])로 변환한 값. 예: "고양이" → [0.12, -0.45, 0.78, ...]
--   의미가 비슷한 문장일수록 두 배열이 가리키는 방향(벡터)이 서로 가깝다.
--
-- ── vector(1536)이란? ────────────────────────────────────────
--   pgvector가 제공하는 타입. 괄호 안 숫자는 "차원 수"(배열 길이).
--   text-embedding-3-small 모델은 항상 1536개의 float를 반환하므로 1536.
--
--   다른 모델을 쓰면 차원이 달라진다:
--     text-embedding-ada-002       → 1536차원
--     text-embedding-3-small       → 1536차원  ← 이 POC
--     text-embedding-3-large       → 3072차원
--     OpenAI text-embedding-3-*    → 차원 축소 옵션 있음(256~3072)
--
--   ※ 모델을 바꾸거나 차원을 변경하면 document_chunks.embedding 컬럼을 재생성해야 한다.
--     기존 데이터와 차원이 다른 벡터는 저장·검색 모두 불가능하다.
--
-- ── 테이블 분리 설계 ─────────────────────────────────────────
--   documents       : 원본 문서 (소스 관리, 인덱싱 상태 추적)
--   document_chunks : 청크 + 벡터 (실제 검색 대상)
--
--   documents.status: pending → processing → indexed | failed
--   ON DELETE CASCADE: documents 삭제 시 document_chunks 자동 삭제
--

-- 원본 문서 테이블
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

-- 청크 + 벡터 테이블
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


-- ══════════════════════════════════════════════════════════════
-- [4] 벡터 검색 인덱스
-- ══════════════════════════════════════════════════════════════
--
-- ── 왜 인덱스가 필요한가? ────────────────────────────────────
--   인덱스 없이 벡터 검색(정확 탐색, Exact KNN)을 하면
--   모든 행을 순차적으로 읽어 거리를 계산한다 → O(N).
--   문서가 수만 건을 넘으면 검색 시간이 급격히 늘어난다.
--   인덱스를 쓰면 "근사(Approximate) 탐색"으로 속도를 크게 줄인다.
--
-- ── pgvector의 인덱스 종류 ───────────────────────────────────
--
--   1) IVFFlat (Inverted File Flat)
--      - 학습 단계에서 벡터를 lists개의 클러스터로 분류한다.
--      - 검색 시 가장 가까운 probe개 클러스터만 탐색 → 속도 향상.
--      - 인덱스 빌드가 빠르고 메모리를 적게 쓴다.
--      - 단점: 인덱스 생성 전에 데이터가 어느 정도 있어야 품질이 좋다.
--              (빈 테이블에 만들면 클러스터가 의미 없다 → 나중에 REINDEX 권장)
--
--   2) HNSW (Hierarchical Navigable Small World)  ← 이 POC에서 사용 (pgvector 0.5.0+)
--      - 그래프 기반 인덱스. 검색 정확도(recall)가 IVFFlat보다 높다.
--      - 빈 테이블에 생성해도 데이터 삽입 시 자동으로 그래프를 구성한다.
--      - 빌드 시간이 길고 메모리를 더 쓴다 (m × ef_construction에 비례).
--      - m: 레이어당 최대 연결 수 (기본 16, 높을수록 recall↑ 메모리↑)
--      - ef_construction: 빌드 시 탐색 후보 크기 (기본 64, 높을수록 품질↑ 빌드↓)
--      - 검색 시 SET hnsw.ef_search = N; 으로 탐색 정확도 조정 가능 (기본 40)
--
-- ── 유사도 연산자 종류 ───────────────────────────────────────
--
--   pgvector는 세 가지 거리 계산 방식을 제공한다:
--
--   연산자   ops 이름               수식          값의 범위    의미
--   -------  ---------------------  ------------  -----------  --------------------------
--   <=>      vector_cosine_ops      코사인 거리   0 ~ 2        방향이 같을수록 0에 가까움
--   <->      vector_l2_ops          유클리드 거리 0 ~ ∞        절대 거리(크기 포함)
--   <#>      vector_ip_ops          내적(부호반전) -∞ ~ 0      정규화된 벡터에서 코사인과 동일
--
--   텍스트 의미 검색에는 코사인 유사도(<=>)가 가장 일반적이다.
--   코사인은 벡터의 크기를 무시하고 방향(의미)만 비교하므로
--   문장 길이 차이에 덜 민감하다.
--
--   SQL 사용 예:
--     SELECT title, 1 - (embedding <=> '[0.1,0.2,...]'::vector) AS similarity
--     FROM documents
--     ORDER BY embedding <=> '[0.1,0.2,...]'::vector
--     LIMIT 5;
--
--   ※ MyBatis XML에서 <=> 연산자는 XML 파싱 오류를 막기 위해
--     반드시 <![CDATA[ embedding <=> #{vec}::vector ]]> 로 감싸야 한다.
--
-- ── HNSW 파라미터 튜닝 ──────────────────────────────────────
--
--   m: 레이어당 최대 연결 수. 기본값 16, 범위 2~100.
--     m이 클수록 recall 향상 / 메모리·빌드 시간 증가.
--
--     문서 수   권장 m
--     --------  ------
--      ~ 10만       16  (기본값)
--      ~ 100만      32
--      100만 이상   64
--
--   ef_construction: 빌드 시 동적 후보 목록 크기. 기본값 64, 범위 4~.
--     높을수록 인덱스 품질↑ / 빌드 시간↑. recall 목표 95%+ 시 128 권장.
--
--   hnsw.ef_search: 검색 시 동적 후보 목록 크기. 기본값 40.
--     SET hnsw.ef_search = N; 으로 쿼리 직전 세션에서 조정.
--     높을수록 recall↑ 속도↓. ef_search ≥ topK 권장.
--
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx
    ON document_chunks (document_id);


-- ══════════════════════════════════════════════════════════════
-- [5] 초기 데이터
-- ══════════════════════════════════════════════════════════════
-- admin 계정: admin@poc.com / admin1234 (BCrypt $2b$10$...)
-- WHERE NOT EXISTS → 중복 실행해도 INSERT 스킵
INSERT INTO users (username, email, password, role)
SELECT 'admin',
       'admin@poc.com',
       '$2b$10$3apYfhkAj8ahXoBT8iuGI.x1DAmbKNDucWzBup9bXEVgw.KVSsEly',
       'ADMIN'
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'admin@poc.com'
);
