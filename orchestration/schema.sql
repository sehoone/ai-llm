-- Database schema for the application
-- Generated from SQLModel classes
-- PostgreSQL compatible

-- Create llmonl schema and set as default search path
CREATE SCHEMA IF NOT EXISTS llmonl;
SET search_path TO llmonl, public;

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create user table
CREATE TABLE IF NOT EXISTS "user" (
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
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);
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

-- Create llm_resource table
CREATE TABLE IF NOT EXISTS llm_resource (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    api_base TEXT NOT NULL,
    api_key TEXT NOT NULL,
    deployment_name TEXT,
    api_version TEXT,
    region TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_resource_name ON llm_resource(name);
