# ADR-0015: 장기 메모리 (engine/memory — mem0 + pgvector)

- 상태: Accepted
- 날짜: 2026-11-07
- 결정자: sehoon
- 관련: [ADR-0010](0010-engine-llm-provider.md)(LLM·키), [ADR-0012](0012-engine-rag.md)(pgvector), [ADR-0011](0011-chat-streaming-contract.md)(system prompt 주입), [ADR-0005](0005-ai-engine-layer.md)(경계)
- 참조: V2 `common/langgraph/_memory.py`(MemoryMixin), `chatbot/api/chatbot_api.py`(`DELETE /memory`)
- 로드맵: [v2-chat-migration-roadmap](../v2-chat-migration-roadmap.md) Phase 5

## Context (맥락)

chat이 세션을 넘어 사용자에 대한 사실(이름·선호·맥락)을 **장기 기억**하면 개인화된 답변이 가능하다.
V2는 `mem0ai`(+pgvector)로 사용자별 메모리를 저장하고, 매 턴 마지막 사용자 메시지로 관련 메모리를
검색해 **system prompt에 주입**하며, 턴 종료 후 대화를 메모리에 **추가**한다.

전제:
- 스택에 pgvector 있음(llmonl). mem0는 자체 컬렉션 테이블을 pgvector에 만든다(우리 세션/ORM과 별개 —
  mem0가 자체 관리하는 외부 저장소. langfuse처럼 engine이 외부 인프라를 쓰는 패턴).
- 메모리 추출은 **LLM 호출**(비용·지연) → 기본 **opt-in**.

## Decision (결정)

### 1. engine/memory = mem0 래퍼 (opt-in)

- `engine/memory`: 동기 `mem0.Memory`(V3는 sync) 래퍼. `search(user_id, query)->str`,
  `add(user_id, messages)`, `delete_all(user_id)`. 모든 메서드는 실패를 삼켜 **chat을 막지 않는다**.
- 설정은 `core.config`(env): `MEMORY_ENABLED`(기본 false), 메모리용 LLM·embedder 모델, 컬렉션명,
  최대 보관 수. OpenAI 키는 `LLM_API_KEY` 재사용(ADR-0010).
- vector_store = pgvector(우리 DB, `llmonl` 스키마). mem0가 `public`을 하드코딩하는 `list_cols`를
  `llmonl`로 **몽키패치**(V2 계승). 지연 초기화 싱글턴.
- **dependency**: `mem0ai`. 미설치/미설정이어도 import가 startup을 깨지 않도록 **지연 import**.

### 2. chat 통합 (ADR-0011 system prompt 주입)

- **검색·주입**: `MEMORY_ENABLED`면 `stream_message`가 마지막 사용자 메시지로 메모리를 검색 →
  `load_system_prompt(long_term_memory=...)`로 렌더한 **SystemMessage를 그래프 입력 맨 앞에 추가**.
  `LlmChatModel`은 SystemMessage가 있으면 기본 system prompt를 덧붙이지 않으므로(ADR-0010 §4) 중복 없음.
- **저장**: 턴 종료(`done`) 후 `_run`이 `(user, assistant)` 대화를 메모리에 add(비차단). 추출 LLM 호출이라
  **done 이후**에 수행해 사용자 응답을 지연시키지 않는다.
- **삭제**: `DELETE /api/v1/chat/memory` → 현재 사용자의 모든 메모리 삭제.

### 3. 레이어 (ADR-0005)

AI 능력(메모리 추출·검색)은 engine/memory. 사용자 id·쿼리는 도메인이 값으로 주입. engine은 우리
도메인 테이블/세션을 모른다(mem0 자체 저장소만 사용).

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| 메모리를 user 메시지에 주입(RAG처럼) | V2는 system prompt에 둠(역할상 적절). SystemMessage 주입이 자연스러움. |
| 자체 메모리 구현(요약·벡터) | mem0가 추출·중복제거·검색을 제공. 재발명 불필요. |
| 항상 on | 매 턴 추출 LLM 호출(비용·지연). opt-in이 안전. |
| mem0 전용 벡터스토어(Qdrant 등) | 스택에 없음. pgvector 재사용이 단순. |
| 메모리 추가를 done 이전 | 사용자 응답 지연. done 이후 수행. |

## Consequences (결과)

**긍정**
- 세션 간 개인화(이름·선호 기억). 기존 pgvector·OpenAI 키 재사용. 비차단(실패해도 chat 정상).

**부정 / 리스크**
- `mem0ai` 의존성(+전이 의존). 메모리 add는 추출 LLM 호출(비용·지연) — done 이후지만 연결 유지.
- mem0의 pgvector 스키마 가정(`public`) 몽키패치 의존 — mem0 버전 변화에 취약.
- 정확도·프라이버시: 잘못된 메모리가 주입될 수 있음. 삭제 엔드포인트로 완화. 민감정보 저장 주의.

**후속**
- 프루닝(최대 보관 수) 스윕, 메모리 UI(조회·편집·삭제), 세션/워크스페이스 스코프, 민감정보 필터.
