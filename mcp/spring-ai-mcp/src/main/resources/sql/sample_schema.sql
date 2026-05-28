-- sample_item 테이블 DDL (참고용)
-- ddl-auto: update 설정 시 애플리케이션 기동 시 자동 생성됨
-- ddl-auto: none 사용 시 이 스크립트를 직접 실행

CREATE TABLE IF NOT EXISTS sample_item (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    price       NUMERIC(10, 2)
);

-- 샘플 데이터
INSERT INTO sample_item (name, description, price)
VALUES ('Spring Boot',  'A framework for building Java applications', 79.99),
       ('PostgreSQL',   'Open-source relational database system',      0.00),
       ('MyBatis',      'A SQL mapping framework for Java',            0.00),
       ('Spring AI',    'AI integration library for Spring',           0.00)
ON CONFLICT DO NOTHING;
