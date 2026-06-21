#!/bin/bash
# PostgreSQL 초기화 스크립트 — docker-entrypoint-initdb.d 에서 자동 실행
# postgres 컨테이너 최초 기동 시 1회만 실행됩니다.
set -e

PLATFORM_DB="${POSTGRES_DB}"
MCP_DB="${MCP_DB:-sample_db}"
PUSER="${POSTGRES_USER}"

echo "==> [1/3] spring-ai-mcp 용 DB '$MCP_DB' 생성"
if psql -U "$PUSER" -d "$PLATFORM_DB" -tAc "SELECT 1 FROM pg_database WHERE datname = '$MCP_DB'" | grep -q 1; then
    echo "    '$MCP_DB' 이미 존재 — 건너뜀"
else
    psql -v ON_ERROR_STOP=1 -U "$PUSER" -d "$PLATFORM_DB" -c "CREATE DATABASE \"$MCP_DB\""
    echo "    '$MCP_DB' 생성 완료"
fi

echo "==> [2/3] platform 스키마(llmonl) 및 테이블 생성 → '$PLATFORM_DB'"
psql -v ON_ERROR_STOP=1 -U "$PUSER" -d "$PLATFORM_DB" << 'EOSQL'
CREATE SCHEMA IF NOT EXISTS llmonl;

CREATE TABLE IF NOT EXISTS llmonl.users (
    id               BIGSERIAL    PRIMARY KEY,
    username         VARCHAR(255) NOT NULL,
    email            VARCHAR(255) NOT NULL,
    hashed_password  VARCHAR(255) NOT NULL,
    role             VARCHAR(50)  NOT NULL DEFAULT 'USER',
    status           VARCHAR(50)  NOT NULL DEFAULT 'active',
    created_at       TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at       TIMESTAMP    NOT NULL DEFAULT now(),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email    UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS llmonl.api_key (
    id           BIGSERIAL    PRIMARY KEY,
    user_id      BIGINT       NOT NULL REFERENCES llmonl.users(id),
    key          VARCHAR(255) NOT NULL,
    name         VARCHAR(255) NOT NULL DEFAULT 'API Key',
    expires_at   TIMESTAMP,
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMP,
    usage_count  BIGINT       NOT NULL DEFAULT 0,
    created_at   TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at   TIMESTAMP    NOT NULL DEFAULT now(),
    CONSTRAINT uq_api_key UNIQUE (key)
);

CREATE TABLE IF NOT EXISTS llmonl.refresh_token (
    id          BIGSERIAL    PRIMARY KEY,
    user_id     BIGINT       NOT NULL,
    token       VARCHAR(512) NOT NULL,
    expires_at  TIMESTAMP    NOT NULL,
    is_revoked  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT now(),
    CONSTRAINT uq_refresh_token UNIQUE (token)
);
EOSQL

echo "==> [3/3] mcp 샘플 테이블 생성 → '$MCP_DB'"
psql -v ON_ERROR_STOP=1 -U "$PUSER" -d "$MCP_DB" << 'EOSQL'
CREATE TABLE IF NOT EXISTS sample_item (
    id          BIGSERIAL    PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    price       NUMERIC(10,2)
);

INSERT INTO sample_item (name, description, price)
VALUES ('Spring Boot', 'A framework for building Java applications', 79.99),
       ('PostgreSQL',  'Open-source relational database system',     0.00),
       ('MyBatis',     'A SQL mapping framework for Java',           0.00),
       ('Spring AI',   'AI integration library for Spring',          0.00)
ON CONFLICT DO NOTHING;
EOSQL

echo "==> 초기화 완료"
