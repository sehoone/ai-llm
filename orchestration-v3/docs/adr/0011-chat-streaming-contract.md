# ADR-0011: chat 스트리밍 계약 (토큰·HITL·제목 통합 event-SSE)

- 상태: Accepted
- 날짜: 2026-11-07
- 결정자: sehoon
- 관련: [ADR-0008](0008-chat-human-approval.md)(HITL·SSE 재개), [ADR-0010](0010-engine-llm-provider.md)(engine/llm), [ADR-0005](0005-ai-engine-layer.md)(경계)
- 참조: V2 `chatbot/api/chatbot_api.py`(`chat_stream`), `chatbot/schemas/chat_schema.py`(StreamResponse), `summary_service.py`
- 로드맵: [v2-chat-migration-roadmap](../v2-chat-migration-roadmap.md) Phase 1

## Context (맥락)

Phase 0(ADR-0010)으로 실 LLM이 붙었지만 챗 응답이 **메시지 단위**로 한 번에 온다(생성 완료 후). 또
세션 제목이 항상 "New chat"이다. V2는 토큰 스트리밍·첫 대화 제목 자동생성·아티팩트 이벤트를
단일 SSE에 실어 보냈다(`data: {content,done,type,...}` — 모든 프레임이 `data:`만).

V3는 ADR-0008에서 이미 **event-프레이밍 SSE**(`event: <name>\ndata: {…}`)와 HITL 승인
(`approval_required` → 중단 → `approvals` POST로 재개)를 채택했다. V2의 토큰·제목을 이 틀에
**통합**하되 HITL과 공존해야 한다. web은 이미 `createEventSSEHandler`로 이벤트명 기반 파싱.

제약:
- ADR-0005: 토큰 스트리밍·제목생성은 AI 능력 → `engine`. 영속·HTTP 이벤트화는 `domains/chat`.
- 토큰 스트리밍은 그래프 내부 LLM 호출의 콜백을 타야 한다(LangGraph `stream_mode="messages"`).

## Decision (결정)

### 1. SSE 이벤트 집합 (통합 계약)

| event | data | 의미 |
|-------|------|------|
| `status` | `{phase, filename?}` | **첫 토큰 이전** 서버 진행 단계(§5). `phase ∈ {uploading, extracting, thinking}`. 진행 표시용(본문 아님). |
| `content` | `{delta: str}` | assistant 토큰 조각(진행형). 버블에 이어붙인다. |
| `message` | `{role, content, tool_calls}` | **비스트리밍** 완결 메시지 — tool 결과, 또는 스트리밍 못 한 모델(fake)의 assistant 폴백. |
| `approval_required` | `{group_key, requests[]}` | CONFIRM 도구 — 중단(ADR-0008). |
| `title` | `{title: str}` | 세션 제목(첫 대화 1회). |
| `done` | `{session_id}` | 스트림 종료. |
| `error` | `{detail}` | 오류 종료. |

**assistant 본문은 `content`(토큰) 또는 `message`(폴백) 중 하나로만** 온다(중복 없음). tool 메시지는
`message`로 오며 현재 web은 표시하지 않는다.

### 2. 토큰 스트리밍 메커니즘 — `stream_mode=["updates","messages"]`

그래프를 두 모드로 동시 구동:
- **`messages`**: 노드 내 LLM이 낸 `AIMessageChunk` → 조각 content를 `content` 이벤트로 방출.
- **`updates`**: `__interrupt__`(승인 중단) 감지 + 완결 메시지 **영속**. assistant 완결은 이미
  토큰으로 나갔으므로 **재방출하지 않고 저장만** 한다. tool 메시지는 `message`로 방출+저장.

토큰 콜백이 LLM까지 전파되도록:
- `agent` 노드가 `config`를 받아 `model.invoke(messages, config)`로 전달(ADR-0008 `ChatModel`
  프로토콜을 `invoke(messages, config=None)`로 확장).
- `engine/llm`의 `LlmChatModel.invoke`가 내부 Runnable에 `config`를 포워딩하고, 모델은 `streaming=True`로
  생성(토큰 이벤트 발생 보장).

**폴백**: `FakeToolCallingModel`은 LangChain 모델이 아니라 `messages` 모드가 토큰을 못 잡는다. 이때
`updates`에서 받은 assistant 완결 content를 **단일 `content` 이벤트**로 방출(스트리밍 UX는 없지만
표시는 보장). 즉 "그 메시지에 대해 토큰이 하나도 안 나왔으면 완결본을 content로 보낸다".

### 3. 제목 자동생성 (첫 대화)

`engine/llm/summary.generate_title(question, answer)` — V2 `summary_service` 참조. 기본 모델로 짧은
한국어 제목 생성(실패 시 폴백 "새로운 대화"). `domains/chat`가 **첫 왕복**(이 턴 전 메시지 0건)에서
답변 생성 후 호출 → `chat_session.title` 갱신 → `done` 직전 `title` 이벤트 방출. engine 미구성(키 없음)
이면 생략.

### 4. 레이어 배치 (ADR-0005)

- `engine/graph`: 토큰 스트림을 콜백으로 흘리는 그래프(모델에 config 전달).
- `engine/llm`: `streaming=True` 모델 + `generate_title`.
- `domains/chat/service`: 모드 수신 → SSE 이벤트화, 메시지·제목 영속, 첫 대화 판정.

### 5. 진행 단계 신호 `status` (첫 토큰 이전)

첨부 파일 처리(MinIO 저장·문서 추출, ADR-0016/0017)는 그래프 실행 **이전**에 일어나 첫 토큰까지
수 초의 무표시 구간이 생긴다. `domains/chat/service.stream_message`가 그 사이에 `status` 이벤트를
흘려 사용자에게 단계를 표시한다:

- `uploading` — 첨부 바이트를 MinIO에 저장하기 직전(파일 있을 때만).
- `extracting` — 문서 본문 추출(markitdown) 직전(파일 있을 때만). 단일 파일이면 `filename` 포함.
- `thinking` — 그래프 실행 직전(첫 토큰 대기). 승인 재개(resume) 경로도 이 단계만 방출.

각 yield는 `StreamingResponse` + `X-Accel-Buffering: no`로 즉시 flush되므로, 뒤따르는 blocking
작업(추출 등) **전에** 클라이언트에 도달한다. web은 첫 `content`·`artifact_start`·`approval_required`
(또는 `done`/`error`)에서 표시를 해제한다. `status`는 **진행 표시 전용**이며 assistant 본문이 아니다
(본문 규칙 §1 불변). `onStatus` 미지원 클라이언트는 무시해도 안전(낙관적 로컬 표시로 폴백).

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| V2식 `data:`-only 단일 프레임 유지 | ADR-0008의 event-프레이밍·HITL과 불일치. web은 이미 event 파서. |
| `updates` 모드만(메시지 단위 유지) | 진행형 UX 없음 — Phase 1 목표(토큰 스트리밍) 미달. |
| assistant를 `content`+`message` 둘 다 전송 | 중복 렌더. 하나로만(스트리밍=content, 폴백=message). |
| 토큰 스트리밍을 서비스에서 수동 `astream` | 그래프·HITL·체크포인트와 중복 상태관리. LangGraph 모드가 정석. |
| 제목생성을 도메인에서 LLM 직접 호출 | AI 호출은 engine(ADR-0005). 도메인은 트리거·영속만. |

## Consequences (결과)

**긍정**
- 진행형 토큰 UX + 세션 제목 자동화. HITL·영속 계약 불변(ADR-0008 위에 가산).
- fake 폴백으로 키 없는 로컬·CI·테스트에서도 표시 보장(결정성 유지).
- 단일 SSE 계약으로 web 파서 재사용(이벤트명 분기만 추가).

**부정 / 리스크**
- 토큰 스트리밍은 그래프 내 LLM이 콜백을 타야 함 — `config` 전달·`streaming=True` 전제. provider별
  스트리밍 편차 가능.
- 제목생성은 첫 메시지 종료 시 추가 LLM 호출(지연·비용 소량).

**후속 작업 (Phase 1b+)**
- **per-request 모델 선택**: domain이 `llm_resource_id`→`LlmConfig` 해석·주입(모델 리졸버 refactor).
  `LlmResource`가 provider·api_key·model_name·deployment_name을 보유해 구현 가능.
- 복원력(circuit breaker·fallback), Langfuse 콜백 주입(ADR-0010 후속).
- 아티팩트 이벤트(`artifact_*`)는 Phase 3에서 본 계약에 추가.
