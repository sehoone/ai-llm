# V2 Chat 기능 이식 로드맵

- 상태: Draft (설계 합의용)
- 날짜: 2026-11-07
- 작성자: sehoon / Claude
- 관련 ADR: [0005](adr/0005-ai-engine-layer.md)(engine 레이어), [0007](adr/0007-llm-observability-langfuse.md)(관측), [0008](adr/0008-chat-human-approval.md)(HITL)
- 참조 소스: `orchestration-v2/orchestrator-server/src/{chatbot,rag,common}`

> **목적**: V2 orchestrator의 chat 관련 기능을 V3로 가져오기 위한 단계별 계획. "그대로 복사"가
> 아니라 **V2를 참조해 V3 아키텍처(ADR-0005 engine/domain 분리, ADR-0008 HITL)에 맞게 재작성**한다.
> 각 단계는 선행 의존성과 신규 ADR 초안을 명시한다. **이 문서 합의 후 단계별로 구현**한다.

---

## 1. 현황 vs 목표

### V3 현재 (이식 완료)
- `domains/chat`: 세션 CRUD(생성·목록·이름변경·삭제)·메시지 조회·HITL 승인 스트림. 메시지는
  **role/content/tool_calls 개별 행**(`chat_message`)으로 저장.
- `engine/graph`: HITL 승인 게이트 그래프(`chat_graph.py`) — 모델 노드는 **주입 seam**.
- `engine/agent`: 3-티어 승인 정책·레지스트리(ADR-0008).
- `engine/observability`: Langfuse 계측(ADR-0007).
- 모델 노드는 `FakeToolCallingModel` — **실제 LLM 호출 없음**.
- web `features/chats`: 토큰 스트림·승인 다이얼로그 처리. 아티팩트 UI·RAG 그룹 셀렉터 보유(백엔드 대기).

### V2 chat 기능 전수 (이식 대상)
| 기능 | V2 위치 (LOC) | 핵심 의존 |
|------|---------------|-----------|
| 토큰 스트리밍 챗 | `chatbot/api/chatbot_api.py` (628) | `LangGraphAgent` |
| 실 LLM 호출·모델선택 | `common/services/llm.py` (589) | provider SDK, `llm_resource` |
| LangGraph 에이전트 | `common/langgraph/graph.py`(455)·`_nodes.py`(150) | LLMService, tools |
| 장기 메모리(mem0) | `common/langgraph/_memory.py` (185) | mem0 |
| RAG | `rag/services/rag_service.py`(895) + rag 도메인(~2275 전체) | pgvector, embedding(153) |
| 제목 자동생성 | `chatbot/services/summary_service.py` (32) | LLM |
| 아티팩트 스트리밍 | `chatbot/services/artifact_stream_parser.py` (180) + artifact 테이블 | — |
| 파일 첨부(비전/텍스트/PDF) | `chatbot/services/file_storage_service.py`(64)·`attachment_repository.py`(81) | 스토리지 |
| 관리자 대화이력 | `chatbot/schemas/admin_schema.py` + DB | — |
| Custom GPTs | `chatbot/api/custom_gpts.py` (446) + gpt 모델/서비스 | LLMService |

---

## 2. 핵심 아키텍처 결정 (단계 공통)

이식 전 반드시 합의해야 할 긴장점:

### (A) V2 `LangGraphAgent`(모놀리식) → V3 engine 분해
V2는 LLM·RAG·메모리·그래프·툴이 `LangGraphAgent` 한 클래스에 뭉쳐 있고 `chatbot` API가 직접 들고
쓴다. V3는 ADR-0005에 따라 `engine/{llm,rag,memory,graph,agent}`로 **분리**하고 `domains`는
HTTP·영속만. engine은 `domains`·FastAPI를 import 금지(`import-linter`로 강제). → **그대로 못 옮긴다.
기능별로 engine 모듈에 재배치**하고, 컨텍스트(역할·모델·rag_group)는 도메인이 **값으로 주입**.

### (B) 데이터 모델: Q&A 쌍 → 개별 메시지
V2 `chat_message`는 `(question, answer)` 한 행 = 한 왕복. V3는 role/content 개별 행(HITL·tool
메시지 수용). → **V3 모델 유지.** V2 이력/관리자 조회는 V3 스키마 위에서 재구성(쌍 복원은 user+다음
assistant 묶기). 세션 id는 V2 문자열(uuid) → **V3 int 유지.**

### (C) 스트리밍 계약 통합
V2 SSE: `data: {content,done,type,...}`(모든 프레임 `data:`만). V3 SSE: `event: <name>\ndata:{…}`
(message·approval_required·done·error). 토큰·아티팩트·제목 이벤트를 **V3 event-프레이밍으로 통합**
해야 한다(→ 신규 ADR, §4 Phase 1). web은 이미 `createEventSSEHandler`로 event 기반 파싱.

### (D) RAG 주입 방식: 검색 "도구"(AUTO 티어) vs 사전 컨텍스트 주입
V2는 `rag_group`을 받아 사전 검색 후 프롬프트에 주입. V3 HITL 구조에선 **RAG 검색을 AUTO 티어 도구**
로 노출하는 편이 ADR-0008과 정렬(읽기·안전 → 승인 불필요, 관측·재사용 용이). 사전 주입 방식과
트레이드오프를 Phase 2 ADR에서 확정.

---

## 3. 의존성 그래프 (선후관계)

```
Phase 0 engine/llm + prompts  ← 모든 실기능의 게이트
   │
   ├─▶ Phase 1 스트리밍 챗 + 제목생성        (engine/llm만 필요)
   │       │
   │       ├─▶ Phase 2 RAG        (engine/rag + rag 도메인 + pgvector)
   │       ├─▶ Phase 3 아티팩트    (파서 + artifact 도메인)
   │       └─▶ Phase 4 첨부/멀티모달 (스토리지 + 비전)
   │
   ├─▶ Phase 5 장기 메모리(mem0)   (engine/memory, 독립)
   └─▶ Phase 6 관리자 이력          (Phase 1 데이터 위, 독립)

Phase 7 Custom GPTs   ← 별도 대형 트랙 (engine/llm 재사용, 독립 로드맵)
```

Phase 1 완료 시점에 **"실제로 답하는 챗"**이 됨(현재 데모 승인 흐름 → 실 LLM 대화). 2~4는 Phase 1
위에서 병렬 가능.

---

## 4. 단계별 계획

### Phase 0 — engine/llm + prompts (기반) — ✅ 구현됨 (2026-11-07)
**목표**: 실제 LLM 호출 능력을 engine에 심는다. ADR-0005 경계 준수. → [ADR-0010](adr/0010-engine-llm-provider.md)
- `engine/llm/`: V2 `common/services/llm.py`(589) 참조 → **LiteLLM provider 통합**(`LlmConfig`·
  `build_chat_model`·`LlmChatModel` 동기 어댑터). **설정은 값 주입/`core.config`(env)** — engine은
  `llm_resource` 테이블·요청을 모름(DB 조회는 domain, Phase 1).
- `engine/prompts/`: V2 `system.md` 트림 이식 + `load_system_prompt` 로더.
- `domains/chat/service.py`: `settings.llm_is_configured` 토글 — 키 있으면 실 LLM, 없으면
  `FakeToolCallingModel` 폴백(로컬·CI·HITL 테스트 불변).
- **ADR-0010 §5 의도적 비포함**: 도구 바인딩·토큰 단위 SSE·per-request 모델 선택·복원력
  (circuit breaker 등)·Langfuse 콜백 주입 → **Phase 1+**.
- 리스크: `langchain-litellm` 신규 의존(`uv sync` 필요)·provider SDK 호환.

### Phase 1 — 스트리밍 챗 + 제목 자동생성 — ✅ 구현됨 (2026-11-07)
**목표**: 사용자가 실제 답변을 토큰 스트림으로 받고, 첫 대화 시 제목 자동 생성. → [ADR-0011](adr/0011-chat-streaming-contract.md)
- **토큰 SSE**: 그래프 `stream_mode=["updates","messages"]` — `content`(토큰 delta) 이벤트.
  모델에 `config` 전달 + `streaming=True`로 토큰 콜백 전파. 비스트리밍(fake)은 완결본을 content로 폴백.
- 제목생성: `engine/llm/summary.generate_title`(V2 `summary_service` 참조). 첫 왕복 후 도메인이
  트리거 → 세션 title 갱신 + `title` 이벤트.
- web: `ChatStreamCallbacks`에 `onContent`·`onTitle` 추가, `index.tsx` 토큰 누적·제목 갱신. 승인 흐름 유지.
- **ADR-0011 §4 후속**: 복원력(circuit breaker·fallback)·Langfuse 콜백 주입.

### Phase 1b — per-request 모델 선택 — ✅ 구현됨 (2026-11-07)
**목표**: 요청별로 특정 `llm_resource`를 골라 chat에 사용.
- `engine/graph`: `build_chat_graph(model=...)`가 **리졸버 함수**(`config→ChatModel`)도 허용. agent 노드가
  `config.configurable["llm_config"]`로 모델 선택(engine은 DB 미조회 — 도메인이 값 주입, ADR-0005).
- `domains/chat`: `MessageRequest.llm_resource_id` → `LlmResourceRepository`로 해석 → `LlmConfig` 주입.
  frozen `LlmConfig` 키로 모델 캐시. 미지정/비활성/비chat이면 기본 모델 폴백.
- web: `streamMessage(…, llmResourceId)` + `index.tsx`가 `selectedModelId` 전달(모델 셀렉터 연동).
- 검증: chat 리소스 seed → `llm_resource_id`로 전송 → 해당 리소스로 응답 확인.
- **한계**: 승인(HITL) **재개**는 `llm_resource_id`를 안 싣어 기본 모델로 이어감(실모델은 현재 도구
  미바인딩이라 승인 미발생 → 영향 없음). 실도구 도입(Phase 2+) 시 세션에 선택 모델 보존 필요.

### Phase 2 — RAG → [ADR-0012](adr/0012-engine-rag.md)
**목표**: chat이 RAG 그룹 대상으로 검색·답변. rag-documents 화면 복원. **사전 주입 방식**(§2D 결정).

#### Phase 2a — 백엔드 foundation — ✅ 구현됨 (2026-11-07)
- DDL: `rag_group_config`·`rag_key_config`·`document`·`rag_embedding(vector 1536)` (init.sql + 라이브 DB 적용).
- `engine/rag/`: `chunk_text`(순수) + `embed_texts`/`embed_query`(LiteLLM, LlmConfig 주입). DB 미의존.
- `domains/rag/`: 그룹·키·문서 CRUD + 수집(chunk→embed→store) + 벡터 검색(pgvector `<=>`), `/api/v1/rag/*` 등록.
  임베딩 리소스(`resource_type="embedding"` llm_resource) 해석·주입.
- 검증: embedding 리소스 seed → 그룹/키 생성 → 문서 수집 → 벡터 검색(유사도 반환) 확인.

#### Phase 2b — chat 연동 + web — ✅ 구현됨 (2026-11-07)
- chat 사전 주입: `MessageRequest.rag_group` → `RagService.rag_context`로 검색해 그래프 입력에
  "Context from knowledge base:" 프리펜드(원문은 clean 영속). 임베딩 미설정/검색 실패는 비차단(빈 컨텍스트).
- web: chats `loadRagGroups` 복원(`ragGroupApi.listGroups`), `streamMessage(…, ragGroup)` + `selectedRagGroup` 전달.
  `rag-groups.ts`는 `/api/v1/rag/*`와 경로·메서드(PUT) 정렬돼 그대로 동작.
- 검증: 동일 질문을 rag_group 유/무로 대조 → 무(일반 추측) vs 유(업로드 PTO 문서 기반 정확 답변) 확인.
- **남은 web(후속)**: rag-documents 화면의 문서 업로드 UI 계약(`/rag/documents`) 정렬·검증.

### Phase 3 — 아티팩트 → [ADR-0013](adr/0013-artifacts.md)
**목표**: 코드/문서/다이어그램 아티팩트 스트리밍·영속·버전.

#### Phase 3a — 백엔드 foundation — ✅ 구현됨 (2026-11-07)
- DDL: `artifact`·`artifact_version`·`artifact_data`(session_id/message_id BIGINT 적응) — init.sql + 라이브.
- `engine/artifact/parser.py`: V2 `ArtifactStreamParser` 이식(순수 상태머신) + 단위 테스트.
- `domains/artifact/`: model·repository(upsert_version·버전·publish·data·delete)·service·schema·api(+public), `/api/v1/artifacts`·`/api/v1/public/artifacts` 등록.
- 검증: 파서(분할 태그) + upsert v1→v2 버전증가 + 목록/상세/버전/publish 공개뷰 확인.

#### Phase 3b — chat 스트림 통합 — ✅ 구현됨 (2026-11-07)
- `domains/chat/service._run`: 토큰을 `ArtifactStreamParser`로 흘려 `content`/`artifact_start|delta|end`
  SSE 분기, END 시 `upsert_version` 영속·message 링크, assistant 메시지엔 **칩 포함 display 본문** 저장.
- `engine/prompts/system.md`: 아티팩트 지시 복원(모델이 `<artifact>` 방출).

#### Phase 3c — web 재배선 — ✅ 구현됨 (2026-11-07)
- `ChatStreamCallbacks.onArtifact` + `chat.ts` artifact 이벤트 디스패치 + `index.tsx` artifact-store 연결
  (start/delta/end) + `syncArtifactServerIds`. 라이브러리·패널·스토어는 기존.
- 검증: mermaid 아티팩트 생성 → artifact_start 1/delta 19/end 1 분리, 캔버스 본문·버전 영속, 메시지엔 칩만.

#### Phase 3d — 인터랙티브 데이터 / 공개 링크 (선택·후속)
- `artifact_data` 저장(`window.artifactData` 호스트 API)·공개 샌드박스 렌더 보안. publish/public 백엔드는 구현됨(3a).

### Phase 4 — 첨부/멀티모달 — ✅ 구현됨 (2026-11-07) → [ADR-0014](adr/0014-attachments-multimodal.md)
**목표**: 이미지(비전)·텍스트 첨부 채팅. (PDF는 placeholder — V2 동일)
- 저장: **로컬 볼륨**(`UPLOAD_DIR`, V2 계승; MinIO/S3는 어댑터 후속). `core/storage.FileStorage`.
- DDL: `chat_attachment`(init.sql+라이브), compose api에 `api-uploads` 볼륨.
- `domains/chat`: `MessageRequest.files`(base64), 첨부 영속, **멀티모달 그래프 입력**(이미지=`image_url`
  data URI, 텍스트=추출), 메시지 응답에 `attachments`, `GET /chat/attachments/{id}` 다운로드(인가).
- web: `handleSendMessage` 파일 base64 복원 + `streamMessage(…, files)`, `downloadAttachment` v3 경로.
- 검증: 텍스트 추출(BANANA-42) + 비전(생성 PNG→"Blue") + 메타 조회 + 다운로드 확인.

### Phase 5 — 장기 메모리(mem0) — ✅ 구현·검증됨 (2026-11-07) → [ADR-0015](adr/0015-long-term-memory.md)
**목표**: 사용자별 장기 메모리 주입·삭제. **opt-in**(`MEMORY_ENABLED`).
- `engine/memory/`: `mem0.Memory`(sync) 래퍼 — `search`/`add`/`delete_all`, pgvector(llmonl, `list_cols`
  몽키패치), lazy 싱글턴, 지연 import·비차단(V2 `_memory.py` 참조).
- `domains/chat`: 마지막 사용자 메시지로 검색 → system prompt(SystemMessage) 주입, done 후 메모리 적재,
  `DELETE /api/v1/chat/memory`.
- config/deps: `mem0ai>=1.0` + **`psycopg[binary,pool]`**(mem0 pgvector가 psycopg_pool 요구), `MEMORY_*` 설정.
- **검증 중 수정 2건**: ① psycopg_pool 의존성 누락 → `psycopg[binary,pool]`. ② mem0 2.x `search`는
  `filters={"user_id":…}` 필요(`user_id=` 거부) → engine/memory 수정.
- 검증(비파괴): 실행 스택 네트워크·db에 일회용 api 컨테이너로 → 세션 간 회상("Sehoon/keyboards"),
  `DELETE` 후 행 1→0·미회상, `longterm_memory` 자동 생성 확인.

### Phase 6 — 관리자 대화이력
**목표**: 관리자 전체 대화 조회·검색·상세(V2 `/history/all`·`/history/{id}`).
- V2는 Q&A 쌍 기반 → V3는 `chat_message` 위에서 세션·유저 조인으로 재구성(§2(B)).
- `domains/chat`: admin 엔드포인트(`require_admin`), 페이지네이션·검색.
- web: `chat-history` 화면 `/api/v1/*` 재매핑(현재 `v1/chatbot/*` V2-pending 스텁).

### Phase 7 — Custom GPTs (별도 트랙)
**목표**: 사용자 정의 GPT(시스템프롬프트·RAG·모델) + 전용 세션/메시지.
- `domains/gpt`: custom_gpt·gpt_session·gpt_message 모델, V2 `custom_gpts.py`(446)·`custom_gpt_service`(159) 참조.
- engine/llm 재사용. RAG(Phase 2) 의존 시 후순위.
- 범위가 커 **독립 로드맵**으로 분리 권장.

---

## 5. 신규 ADR 목록 (초안 대상)

| ADR | 주제 | Phase |
|-----|------|-------|
| 0010 | engine/llm provider 추상화 + 모델 해석·키 주입 | 0 |
| 0011 | chat 스트리밍 계약(토큰·HITL·제목·아티팩트 통합 event-SSE) | 1 |
| 0012 | engine/rag + rag 도메인(검색 도구화·pgvector·임베딩) | 2 |
| 0013 | 아티팩트(파서·도메인·버저닝) | 3 |
| 0014 | 첨부·멀티모달(MinIO 저장) | 4 |
| 0015 | engine/memory(mem0) | 5 |

> 각 ADR은 해당 Phase 착수 직전 `docs/adr/`에 작성·Accepted 후 구현(CLAUDE.md 규칙: "결정 전 반드시 ADR 참고").

---

## 6. 열린 결정 (합의 필요)

1. **Phase 착수 순서**: 0→1 고정. 그 뒤 2(RAG)·3(아티팩트)·4(첨부) 중 우선순위?
2. **RAG 주입 방식**(§2D): 검색 도구(AUTO) vs 사전 주입 — Phase 2 ADR에서 확정.
3. **첨부 스토리지**(§Phase4): MinIO vs 로컬 볼륨.
4. **Postgres 체크포인터 전환 시점**(ADR-0008 후속): Phase 1에서 함께 or 스케일아웃 직전.
5. **Custom GPTs**(Phase 7): 이번 이식 범위 포함 여부(별도 트랙 권장).

---

## 7. 다음 액션

- [x] 본 로드맵 리뷰·§6 결정 합의.
- [x] ADR-0010 작성 → Phase 0 착수(engine/llm + 실모델 토글).
- [x] **Phase 0 완료 기준**: `LLM_API_KEY` 설정 시 chat이 `FakeToolCallingModel` 없이 실 LLM로
      응답(메시지 단위; 토큰 SSE는 Phase 1). 키 없으면 데모 모델 유지.
- [x] `uv lock`(docker)로 `langchain-litellm` 설치 → 배포 후 실 LLM 스모크(답변 확인).
- [x] ADR-0011 작성 → Phase 1 구현(토큰 SSE + 제목생성). 스모크: content 14조각 + title 자동생성 확인.
- [x] Phase 1b: per-request 모델 선택(`llm_resource_id`→`LlmConfig` 주입). 검증 완료.
- [ ] §6 우선순위 결정 → Phase 2(RAG) / 3(아티팩트) / 4(첨부) 중 착수.
