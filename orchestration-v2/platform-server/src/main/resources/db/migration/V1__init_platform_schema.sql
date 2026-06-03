-- Platform Server 소유 테이블 초기화
-- orchestrator-server(SQLModel)와 공유 DB를 사용하므로 IF NOT EXISTS로 안전하게 처리

CREATE SCHEMA IF NOT EXISTS llmonl;

-- users
CREATE TABLE IF NOT EXISTS llmonl.users (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password TEXT         NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'USER',
    status          VARCHAR(20)  NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email    ON llmonl.users (email);
CREATE INDEX IF NOT EXISTS idx_users_username ON llmonl.users (username);

-- api_key
CREATE TABLE IF NOT EXISTS llmonl.api_key (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT       NOT NULL,
    key        VARCHAR(255) NOT NULL UNIQUE,
    name       VARCHAR(100) NOT NULL DEFAULT 'API Key',
    expires_at TIMESTAMP,
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_key_user_id ON llmonl.api_key (user_id);
CREATE INDEX IF NOT EXISTS idx_api_key_key     ON llmonl.api_key (key);

-- refresh_token (platform-server 신규 테이블)
CREATE TABLE IF NOT EXISTS llmonl.refresh_token (
    id         BIGSERIAL    PRIMARY KEY,
    user_id    BIGINT       NOT NULL,
    token      VARCHAR(512) NOT NULL UNIQUE,
    expires_at TIMESTAMP    NOT NULL,
    is_revoked BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_refresh_token_user_id ON llmonl.refresh_token (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_token_token   ON llmonl.refresh_token (token);

-- llm_resource
CREATE TABLE IF NOT EXISTS llmonl.llm_resource (
    id              BIGSERIAL    PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(20)  NOT NULL DEFAULT 'chat',
    model_name      VARCHAR(100),
    provider        VARCHAR(50)  NOT NULL,
    api_base        TEXT         NOT NULL,
    api_key         TEXT         NOT NULL,
    deployment_name VARCHAR(100),
    api_version     VARCHAR(20),
    region          VARCHAR(50),
    priority        INT          NOT NULL DEFAULT 0,
    weight          INT          NOT NULL DEFAULT 1,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_resource_type     ON llmonl.llm_resource (resource_type);
CREATE INDEX IF NOT EXISTS idx_llm_resource_active   ON llmonl.llm_resource (is_active);
