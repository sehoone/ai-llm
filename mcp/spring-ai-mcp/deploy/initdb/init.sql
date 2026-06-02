-- PostgreSQL 컨테이너 최초 기동 시 자동 실행 (docker-entrypoint-initdb.d)
-- ddl-auto: validate 환경에서 앱 기동 전 스키마를 미리 생성한다.

CREATE TABLE IF NOT EXISTS sample_item (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    price       NUMERIC(10, 2)
);

INSERT INTO sample_item (name, description, price)
VALUES ('Spring Boot',  'A framework for building Java applications', 79.99),
       ('PostgreSQL',   'Open-source relational database system',      0.00),
       ('MyBatis',      'A SQL mapping framework for Java',            0.00),
       ('Spring AI',    'AI integration library for Spring',           0.00)
ON CONFLICT DO NOTHING;
