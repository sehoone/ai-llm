# Architecture Decision Records (ADR)

orchestration-v3의 주요 아키텍처 결정을 기록합니다. 각 ADR은 결정 당시의 맥락·대안·결과를 담으며,
결정이 바뀌면 새 ADR로 기존 것을 `Superseded` 처리합니다(기존 파일은 보존).

## 형식

[MADR](https://adr.github.io/madr/) 변형을 사용합니다: **Context → Decision → Alternatives → Consequences**.

## 상태 값

`Proposed` → `Accepted` → (`Superseded by ADR-XXXX` | `Deprecated`)

## 목록

| ADR | 제목 | 상태 |
|-----|------|------|
| [0001](0001-monorepo-structure.md) | 모노레포 구조와 태스크 오케스트레이션(moon) | Superseded by 0003 |
| [0002](0002-polyglot-and-auth-boundary.md) | 폴리글랏 3서비스 유지와 인증 경계 | Superseded by 0003 |
| [0003](0003-single-python-backend.md) | 단일 Python 백엔드 + 사내 IdP 인증 위임 | Accepted (구조는 0004 개정, 인증은 0009 대체) |
| [0004](0004-apps-packages-monorepo-layout.md) | apps/* + packages/* 모노레포 레이아웃 채택 | Accepted |
| [0005](0005-ai-engine-layer.md) | AI 엔진 레이어 분리 (domains ↔ engine) | Accepted |
| [0006](0006-web-structure-and-oidc.md) | 프론트 구조(shadcn-admin) 및 OIDC 리다이렉트 인증 | Accepted (인증 흐름은 0009 대체) |
| [0007](0007-llm-observability-langfuse.md) | LLM 관측(Observability)을 Langfuse에 위임 | Accepted |
| [0008](0008-chat-human-approval.md) | 챗 사용자 승인(Human-in-the-Loop) | Accepted |
| [0009](0009-self-id-password-auth.md) | 자체 ID/PW 인증 (IdP 위임에서 전환) | Accepted |
| [0010](0010-engine-llm-provider.md) | engine/llm — provider 추상화 + 모델 해석·주입 경계 | Accepted |
| [0011](0011-chat-streaming-contract.md) | chat 스트리밍 계약 (토큰·HITL·제목 통합 event-SSE) | Accepted |
| [0012](0012-engine-rag.md) | RAG — 검색 증강 (engine/rag + rag 도메인, pgvector) | Accepted |
| [0013](0013-artifacts.md) | 아티팩트 (스트림 파서 + artifact 도메인 + 버저닝) | Accepted |
| [0014](0014-attachments-multimodal.md) | 첨부/멀티모달 (이미지 비전 + 텍스트, 로컬 저장) | Accepted (저장은 0017로 개정) |
| [0015](0015-long-term-memory.md) | 장기 메모리 (engine/memory — mem0 + pgvector) | Accepted |
| [0016](0016-document-text-extraction.md) | 문서 본문 추출 (engine/extraction — markitdown) | Accepted |
| [0017](0017-attachment-object-storage-minio.md) | 첨부 객체 스토리지 (MinIO / S3 호환) | Accepted (0014 §1·§4 개정) |
| [0018](0018-env-config-layout.md) | env 설정 레이아웃 — 환경별 단일 소스 | Accepted |
| [0019](0019-workflow-engine.md) | 워크플로우 — 노드 그래프 실행 엔진 + workflow 도메인 | Accepted |
| [0020](0020-user-portal-frontend.md) | 사용자 포털 프론트 분리 (apps/portal — 경로 분리·셀프 가입) | Accepted |
| [0021](0021-projects.md) | 프로젝트 — 대화·지침·지식 작업공간 (chat 재사용 + project 도메인) | Accepted |
| [0022](0022-connectors-mcp.md) | 커넥터 — 챗 도구를 사내 MCP 서버로 확장 (connector 도메인 + engine MCP 로더) | Accepted |
| [0023](0023-admin-portal-split.md) | 관리자/사용자 포털 분리 (admin web ↔ user portal — 상위 아키텍처 결정) | Accepted |
| [0024](0024-skills-instruction-presets.md) | 스킬 — 재사용 지침 프리셋 (skill 도메인 + system prompt 합성) | Accepted |
| [0025](0025-chat-clarification-and-interrupt.md) | 챗 되묻기·사람 개입 (ask_user 인터럽트 + 중단 내구화) | Accepted |
| [0026](0026-chat-async-streaming.md) | chat 비동기 스트리밍 전환 (취소 가능한 중단 — ADR-0011 §2 개정) | Accepted |
| [0027](0027-async-db-session.md) | 비동기 DB 세션 (AsyncSession/psycopg async — 단계적·조건부) | Proposed |
| [0028](0028-langgraph-postgres-checkpointer.md) | LangGraph Postgres 체크포인터 (AsyncPostgresSaver — 세션 내구화) | Accepted |
| [0029](0029-chat-checkpointer-operations.md) | chat 체크포인터·승인 운영 (정리·기동 경쟁·관측) | Proposed |
| [0030](0030-plugins.md) | 플러그인 — 설치형 능력 번들 + 마켓플레이스 (plugin 도메인 + 거버넌스) | Proposed |
| [0031](0031-structured-logging-and-request-context.md) | 구조화 로깅 + 요청 상관관계 (core/logging + request_id contextvar + 액세스 로그) | Proposed |
| [0032](0032-production-readiness.md) | 상용 배포 준비 (예외 핸들러·헬스 분리·하드닝 + Phase2·3 로드맵) | Proposed |

## 관련 문서

- [`../v2-chat-migration-roadmap.md`](../v2-chat-migration-roadmap.md) — V2 chat 기능 이식 단계별 로드맵(ADR-0010~0015 매핑).

- [`../portal-roadmap.md`](../portal-roadmap.md) — 사용자 포털을 "클로드급" 챗 경험으로 끌어올리는 단계별 로드맵(ADR-0020 실행 계획).

- [`../structure-and-references.md`](../structure-and-references.md) — 위 결정들이 업계 표준·사실상 표준과 어떻게 정렬되는지 검증·참조 소스 모음 (ADR이 아닌 레퍼런스).
