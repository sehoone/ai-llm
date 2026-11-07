# ADR-0012: RAG — 검색 증강 (engine/rag + rag 도메인)

- 상태: Accepted
- 날짜: 2026-11-07
- 결정자: sehoon
- 관련: [ADR-0005](0005-ai-engine-layer.md)(경계), [ADR-0010](0010-engine-llm-provider.md)(LiteLLM·LlmConfig), [ADR-0011](0011-chat-streaming-contract.md)(chat 주입 지점), [ADR-0008](0008-chat-human-approval.md)(도구 티어)
- 참조: V2 `rag/services/rag_service.py`, `common/services/embedding.py`, `rag/models/*`, `common/langgraph/graph.py`(`_inject_rag_context`)
- 로드맵: [v2-chat-migration-roadmap](../v2-chat-migration-roadmap.md) Phase 2

## Context (맥락)

chat이 사내 지식베이스를 근거로 답하려면 검색 증강(RAG)이 필요하다. V2는 pgvector에 문서 청크
임베딩을 저장하고, chat 그래프가 `rag_group`으로 검색해 **프롬프트에 컨텍스트를 사전 주입**했다
(`_inject_rag_context` → "Context from knowledge base:" 프리펜드). 도구 호출이 아니다.

제약(ADR-0005): `engine`은 `domains`·FastAPI·DB 세션을 모른다. 그런데 RAG는 (a) 임베딩 호출(AI 능력)과
(b) 벡터 저장·검색(DB)이 섞여 있다 → 레이어를 명확히 가른다.

배포 DB 현황: pgvector 확장 설치됨. RAG 테이블은 아직 없음(init.sql에 "후속"으로 비워둠). DB는
기존 볼륨이라 init.sql이 재실행되지 않음 → **DDL을 라이브 DB에도 직접 적용** 필요.

## Decision (결정)

### 1. 주입 방식 = 사전 주입(pre-injection), 도구 아님

`rag_group`이 주어지면 **도메인이 검색해 컨텍스트를 그래프 입력(마지막 사용자 메시지)에 사전 주입**한다
(V2 계승). 결정적이고, 실모델에 도구를 바인딩하지 않아도 동작한다(현재 도구 미바인딩 — ADR-0011).

> **대안(RAG-as-AUTO-tool)**: ADR-0008 티어(AUTO=읽기·안전)와 정렬되지만 모델의 도구호출·바인딩이
> 선행돼야 한다. 실도구 도입 시점에 재검토(후속). Phase 2는 사전 주입으로 단순·확실하게.

### 2. 레이어 분리 (ADR-0005)

- **engine/rag** (순수, DB 미의존):
  - `chunk_text(text)` — 문자 기반 청킹(size 500 / overlap 100, V2 계승).
  - `embed_texts(texts, config)` · `embed_query(text, config)` — LiteLLM 임베딩. `config`는 주입된
    `LlmConfig`(ADR-0010 재사용). provider 중립.
- **domains/rag** (HTTP·영속·DB):
  - 벡터 insert/search **raw SQL**(pgvector `<=>`, `1 - distance` 유사도)은 repository.
  - service가 수집(chunk→embed→store)·검색(embed query→vector search)·그룹/키 CRUD 오케스트레이션.
  - **임베딩 리소스 해석**: `resource_type="embedding"` llm_resource → `LlmConfig` 주입(chat 모델 해석과 동일 패턴, ADR-0011 §4). 없으면 명확한 오류.

### 3. 데이터 모델 (pgvector, schema llmonl) — V2 계승

| 테이블 | 핵심 컬럼 | 용도 |
|--------|-----------|------|
| `rag_group_config` | id(uuid), user_id, name, description, color | UI 그룹 |
| `rag_key_config` | id(uuid), user_id, rag_key, rag_group, rag_type | 그룹 내 키(=하나의 RAG) |
| `document` | id, user_id?, rag_key, rag_group, rag_type, filename, content, doc_metadata | 원문 |
| `rag_embedding` | id, doc_id, rag_key, rag_group, rag_type, chunk_index, content, **embedding vector(1536)** | 청크 임베딩 |

- 임베딩 차원 **1536 고정**(OpenAI text-embedding-3-small/ada-002). 다른 차원 모델은 후속(컬럼 차원·재색인 필요).
- `rag_type`: `chatbot_shared`(전역) | `user_isolated`(사용자별). Phase 2는 shared 중심, user 필터 지원.
- web 계약(`src/api/rag-groups.ts`)의 필드(name·color·rag_key·rag_group·doc_count 등)와 정렬.

### 4. 하위 단계

- **2a(이번)**: DDL + engine/rag + rag 도메인(그룹/키 CRUD·문서 업로드/수집·검색 API) + 등록. API로 검증.
- **2b(후속)**: chat 사전 주입(`MessageRequest.rag_group` → 도메인이 검색·주입) + web(rag-documents 화면 재매핑, chats의 `loadRagGroups`·rag 셀렉터 복원).

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| RAG-as-AUTO-tool | 도구 바인딩·모델 도구호출 선행 필요(현재 미바인딩). 사전 주입이 즉시 동작·결정적. |
| 벡터 검색을 engine에 | engine이 DB를 알게 됨 — ADR-0005 위반. 검색은 pgvector SQL = domain. |
| V2 `rag_service`(895) 1:1 이식 | `database`·전역 싱글턴 결합. V3는 세션 주입·레이어 분리로 린하게 재작성. |
| SQLModel create_all로 테이블 생성 | V3는 init.sql 기반(ADR 관행). pgvector `vector` 타입은 raw DDL이 명확. |
| 임베딩 차원 동적 | 컬럼 타입 고정이 단순·성능적. 모델 전환은 재색인 포함 후속. |

## Consequences (결과)

**긍정**
- chat이 지식베이스 근거로 답변 가능(사전 주입). engine 순수성 유지(임베딩만, DB는 domain).
- LiteLLM로 임베딩 provider 중립. web 계약과 필드 정렬로 재매핑 수월.

**부정 / 리스크**
- 임베딩 차원 1536 고정 — 모델 전환 시 재색인 필요.
- 사전 주입은 항상 검색(지연·비용) — 쿼리 변환·캐싱·관련성 임계값은 후속.
- DDL을 라이브 DB에 수동 적용(볼륨 기존) — init.sql은 신규 볼륨용.
- 복원력(circuit breaker·weighted)·쿼리 변환(query_transformer)·자연어검색은 후속(V2 대비 축소 이식).

**후속 작업**
- 2b: chat 사전 주입 + web.
- 쿼리 변환·관련성 임계값·재랭킹, user_isolated 전체 흐름, RAG-as-tool 재검토, 임베딩 차원 유연화.
