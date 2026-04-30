-- Database schema for the application
-- Generated from SQLModel classes
-- PostgreSQL compatible

-- Create llmonl schema and set as default search path
CREATE SCHEMA IF NOT EXISTS llmonl;
SET search_path TO llmonl, public;

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create session table
CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create gpt_session table
CREATE TABLE IF NOT EXISTS gpt_session (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    custom_gpt_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gpt_session_user_id ON gpt_session(user_id);
CREATE INDEX IF NOT EXISTS idx_gpt_session_custom_gpt_id ON gpt_session(custom_gpt_id);

-- Create thread table
CREATE TABLE IF NOT EXISTS thread (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create document table for RAG storage
CREATE TABLE IF NOT EXISTS document (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    rag_key TEXT NOT NULL,
    rag_group TEXT NOT NULL,
    rag_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    content TEXT NOT NULL,
    doc_metadata TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create rag_embedding table for storing vector embeddings
CREATE TABLE IF NOT EXISTS rag_embedding (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL,
    rag_key TEXT NOT NULL,
    rag_group TEXT NOT NULL,
    rag_type TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_session_user_id ON session(user_id);
CREATE INDEX IF NOT EXISTS idx_document_user_id ON document(user_id);
CREATE INDEX IF NOT EXISTS idx_document_rag_key ON document(rag_key);
CREATE INDEX IF NOT EXISTS idx_document_rag_group ON document(rag_group);
CREATE INDEX IF NOT EXISTS idx_document_rag_type ON document(rag_type);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_doc_id ON rag_embedding(doc_id);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_rag_key ON rag_embedding(rag_key);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_rag_group ON rag_embedding(rag_group);
CREATE INDEX IF NOT EXISTS idx_rag_embedding_rag_type ON rag_embedding(rag_type);

-- Create vector index for fast similarity search (requires pgvector extension)
-- Note: ivfflat index requires at least some data in the table to work properly
-- Run this after inserting initial data:
-- CREATE INDEX IF NOT EXISTS idx_rag_embedding_vector ON rag_embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE chat_message (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_message_session_id ON chat_message(session_id);

CREATE TABLE chat_attachment (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES chat_message(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_attachment_message_id ON chat_attachment(message_id);
CREATE INDEX IF NOT EXISTS idx_chat_attachment_session_id ON chat_attachment(session_id);

CREATE TABLE gpt_chat_message (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gpt_chat_message_session_id ON gpt_chat_message(session_id);

-- Create llm_resource table
CREATE TABLE IF NOT EXISTS llm_resource (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL DEFAULT 'chat',
    model_name TEXT,
    provider TEXT NOT NULL,
    api_base TEXT NOT NULL,
    api_key TEXT NOT NULL,
    deployment_name TEXT,
    api_version TEXT,
    region TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    weight INTEGER NOT NULL DEFAULT 1,
    
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_resource_name ON llm_resource(name);
CREATE INDEX IF NOT EXISTS idx_llm_resource_model_name ON llm_resource(model_name);
CREATE INDEX IF NOT EXISTS idx_llm_resource_resource_type ON llm_resource(resource_type);

-- Create api_key table
CREATE TABLE IF NOT EXISTS api_key (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL DEFAULT 'API Key',
    expires_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create custom_gpt table
CREATE TABLE IF NOT EXISTS custom_gpt (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    instructions TEXT NOT NULL,
    rag_key TEXT NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    model TEXT NOT NULL DEFAULT 'gpt-4-turbo',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_custom_gpt_user_id ON custom_gpt(user_id);
CREATE INDEX IF NOT EXISTS idx_custom_gpt_rag_key ON custom_gpt(rag_key);

-- ── Agent system ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS agent (
    id          TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    system_prompt      TEXT,
    welcome_message    TEXT,
    model              VARCHAR(100) NOT NULL DEFAULT 'gpt-4o',
    temperature        FLOAT NOT NULL DEFAULT 0.7,
    max_tokens         INTEGER NOT NULL DEFAULT 2000,
    rag_keys           TEXT[] NOT NULL DEFAULT '{}',
    rag_groups         TEXT[] NOT NULL DEFAULT '{}',
    rag_search_k       INTEGER NOT NULL DEFAULT 5,
    rag_enabled        BOOLEAN NOT NULL DEFAULT FALSE,
    tools_enabled      JSON NOT NULL DEFAULT '[]',
    is_published       BOOLEAN NOT NULL DEFAULT FALSE,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_user_id ON agent(user_id);

CREATE TABLE IF NOT EXISTS agent_session (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL REFERENCES agent(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL,
    name        TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_session_agent_id ON agent_session(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_session_user_id ON agent_session(user_id);

-- Migration: add rag_groups column to existing agent tables
ALTER TABLE agent ADD COLUMN IF NOT EXISTS rag_groups TEXT[] NOT NULL DEFAULT '{}';

-- ── RAG group / key config ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rag_group_config (
    id          TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    color       VARCHAR(20) NOT NULL DEFAULT '#6366f1',
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_rag_group_user_name UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_rag_group_config_user_id ON rag_group_config(user_id);

CREATE TABLE IF NOT EXISTS rag_key_config (
    id          TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    rag_key     VARCHAR(200) NOT NULL,
    rag_group   VARCHAR(100) NOT NULL,
    description TEXT,
    rag_type    VARCHAR(50) NOT NULL DEFAULT 'chatbot_shared',
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_rag_key_user UNIQUE (user_id, rag_key)
);

CREATE INDEX IF NOT EXISTS idx_rag_key_config_user_id ON rag_key_config(user_id);
CREATE INDEX IF NOT EXISTS idx_rag_key_config_rag_group ON rag_key_config(rag_group);

-- ── Workflow engine ───────────────────────────────────────────────────────────

-- Workflow definitions (node/edge graph stored as JSONB)
CREATE TABLE IF NOT EXISTS workflow (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    definition JSONB NOT NULL DEFAULT '{"nodes":[],"edges":[]}',
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    webhook_token TEXT,             -- NULL = disabled; set to a random token to enable
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workflow_user_id ON workflow(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_updated_at ON workflow(updated_at DESC);

-- Execution records (one per workflow run)
CREATE TABLE IF NOT EXISTS workflow_execution (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|running|completed|failed
    input_data JSONB NOT NULL DEFAULT '{}',
    output_data JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_workflow_execution_workflow_id ON workflow_execution(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_execution_user_id ON workflow_execution(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_execution_created_at ON workflow_execution(created_at DESC);

-- Per-node execution records within a workflow run
CREATE TABLE IF NOT EXISTS workflow_node_execution (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    node_id TEXT NOT NULL,        -- React Flow canvas node id
    node_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|running|completed|failed
    input_data JSONB NOT NULL DEFAULT '{}',
    output_data JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_workflow_node_execution_execution_id ON workflow_node_execution(execution_id);
CREATE INDEX IF NOT EXISTS idx_workflow_node_execution_created_at ON workflow_node_execution(created_at ASC);
CREATE INDEX IF NOT EXISTS idx_workflow_webhook_token ON workflow(webhook_token) WHERE webhook_token IS NOT NULL;

-- Cron schedules for automated workflow triggers
CREATE TABLE IF NOT EXISTS workflow_schedule (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    cron_expr TEXT NOT NULL,        -- "minute hour day month day_of_week"
    input_data JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    next_run_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_workflow_schedule_workflow_id ON workflow_schedule(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_schedule_user_id ON workflow_schedule(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_schedule_active ON workflow_schedule(is_active);

-- Dynamic API endpoint bindings (path+method → workflow)
CREATE TABLE IF NOT EXISTS workflow_endpoint (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    path TEXT NOT NULL,                    -- URL suffix after /api/v1/run/
    method TEXT NOT NULL DEFAULT 'POST',   -- GET | POST | PUT | PATCH | DELETE
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_endpoint_path_method UNIQUE (path, method)
);

CREATE INDEX IF NOT EXISTS idx_workflow_endpoint_workflow_id ON workflow_endpoint(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_endpoint_user_id ON workflow_endpoint(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_endpoint_path_method ON workflow_endpoint(path, method) WHERE is_active = TRUE;

