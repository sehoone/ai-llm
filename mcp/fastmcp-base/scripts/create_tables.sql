-- FastMCP Database Schema
-- PostgreSQL용 테이블 생성 스크립트

-- 데이터베이스 생성 (선택사항)
-- CREATE DATABASE fastmcp_db;

-- 사용자 테이블 생성
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 게시물 테이블 생성
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    author_id INTEGER REFERENCES users(id) ON DELETE CASCADE
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_is_published ON posts(is_published);

-- 샘플 데이터 삽입 (선택사항)
INSERT INTO users (username, email, full_name, is_active) VALUES
    ('admin', 'admin@example.com', 'Administrator', TRUE),
    ('user1', 'user1@example.com', 'Test User 1', TRUE),
    ('user2', 'user2@example.com', 'Test User 2', TRUE)
ON CONFLICT (username) DO NOTHING;

INSERT INTO posts (title, content, is_published, author_id) VALUES
    ('Welcome to FastMCP', 'This is a sample post created by the database MCP server. It demonstrates the basic functionality of the system.', TRUE, 1),
    ('Database Integration', 'Successfully integrated PostgreSQL with SQLAlchemy! This post shows how to work with relational databases.', TRUE, 1),
    ('Getting Started Guide', 'Learn how to use the FastMCP database server for your projects. This guide covers all the essential features.', TRUE, 2),
    ('Hello World', 'My first post! This is an example of a simple blog post.', FALSE, 2),
    ('Advanced Features', 'Exploring advanced database features like raw SQL queries and analytics.', TRUE, 1)
ON CONFLICT DO NOTHING;

-- 권한 설정 (필요시)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_username;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_username;

-- 테이블 정보 확인
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name IN ('users', 'posts')
ORDER BY table_name, ordinal_position;
