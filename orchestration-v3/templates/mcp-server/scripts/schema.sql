-- sample 도메인 DB 예시 스키마 (복제 후 실제 테이블로 교체)
-- V3 공통 컨벤션: llmonl 스키마 사용. 이 템플릿은 create_all 을 호출하지 않으므로
-- 서버 기동 전에 테이블이 존재해야 한다.

CREATE SCHEMA IF NOT EXISTS llmonl;

CREATE TABLE IF NOT EXISTS llmonl.sample_record (
    id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name  VARCHAR(200) NOT NULL,
    value VARCHAR(500)
);

INSERT INTO llmonl.sample_record (name, value) VALUES
    ('sample-a', 'first'),
    ('sample-b', 'second');
