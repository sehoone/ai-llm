-- PostgreSQL 초기화 스크립트 (볼륨이 비어있을 때 최초 1회 실행)
-- llmonl 스키마: platform-server + orchestrator-server 공유
-- keycloak 스키마: Keycloak 전용
CREATE SCHEMA IF NOT EXISTS llmonl;
CREATE SCHEMA IF NOT EXISTS keycloak;
