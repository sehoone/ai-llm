-- Langfuse 전용 데이터베이스 (ADR-0007).
-- 앱 데이터(mydb, llmonl 스키마)와 분리된 별도 DB를 같은 Postgres 인스턴스에 둔다.
-- docker-entrypoint-initdb.d의 스크립트는 POSTGRES_DB(mydb)에 접속해 실행되며,
-- 거기서 CREATE DATABASE가 가능하다. 볼륨이 비어있을 때 최초 1회만 실행됨.
-- (Langfuse가 기동 시 Prisma 마이그레이션으로 스키마를 생성하려면 DB가 먼저 존재해야 한다.)

SELECT 'CREATE DATABASE langfuse'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langfuse')\gexec
