# ADR-0026: chat 비동기 스트리밍 전환 (취소 가능한 중단)

- 상태: Accepted (2026-11-21 stg 실증 — 아래 "검증" 참고)
- 날짜: 2026-11-21
- 결정자: sehoon
- 관련: [ADR-0011](0011-chat-streaming-contract.md)(스트리밍 계약 — §2 메커니즘 개정), [ADR-0025](0025-chat-clarification-and-interrupt.md)(§5 중단 — 한계 해소), [ADR-0008](0008-chat-human-approval.md)(interrupt/재개), [ADR-0005](0005-ai-engine-layer.md)(경계)

## Context (맥락)

ADR-0025 §5에서 "사용자 중단(stop) 시 서버가 생성을 멈추고 부분 응답을 영속"을 시도했으나,
현재 스트리밍이 **동기(sync)**라 신뢰성 있게 동작하지 않는다(ADR-0025 구현 노트):

- chat 그래프는 `_graph.stream(...)`(sync 제너레이터)로 구동되고, FastAPI가 이를 **스레드풀**에서 돌린다.
- 스레드풀의 블로킹 작업은 **강제 취소가 불가**하다. 클라이언트가 연결을 끊어도 모델 생성은 끝까지 진행된다.
- 끊김 감지를 `request.is_disconnected()` 폴링으로 시도했지만 스레드풀 + nginx keepalive 조합에서
  **지연·누락**된다(api 직결은 재현되나 nginx 경유는 불안정).

상용 LLM 챗(claude.ai 류)의 정석은 **end-to-end 비동기 스트리밍**이다: 클라이언트가 fetch를 abort하면
→ 서버의 async 태스크가 **취소(CancelledError)**되고 → 그 취소가 모델 호출(`astream`, httpx 연결)까지
전파돼 **생성·과금이 즉시 멈추며** → 그 시점까지의 부분 답변을 저장한다. async 태스크는 취소가
가능하다는 점이 sync 스레드풀과의 결정적 차이다.

제약:
- **SSE 이벤트 계약(ADR-0011 §1)은 불변** — 이벤트 집합·의미는 그대로. 바뀌는 건 §2 "구동 메커니즘"뿐.
- **프론트(portal) 무변경** — 이미 fetch + AbortController + "중단됨" 배지(ADR-0025)를 갖췄다. abort가
  이제 서버까지 확정적으로 전파될 뿐이다.
- **gpts는 별도 경로**(`LlmChatModel.stream` 직접) — chat 그래프를 쓰지 않으므로 영향 없음. sync 메서드는 보존한다.
- 레이어 경계(ADR-0005) 유지 — AI 실행은 engine, HTTP·영속은 domain.

## Decision (결정)

chat **스트리밍 경로를 end-to-end 비동기로 전환**한다. 클라이언트 연결 종료 → ASGI 태스크 취소 →
`graph.astream` 취소 → 모델 `astream` 중단 → 부분 영속. 범위는 chat 그래프·서비스·API로 한정한다.

### 1. 모델 어댑터에 async 추가 (`engine/llm/model.py`)

`LlmChatModel`에 `ainvoke`(그래프 노드용)를 추가한다. 내부 `ChatLiteLLM`은 async(`ainvoke`/`astream`)를
지원하므로 `await self._runnable.ainvoke(msgs, config=config)`로 위임한다. 기존 `invoke`·`stream`(sync)은
**그대로 보존**(gpts·기타 사용처). `ChatModel` 프로토콜(`engine/graph/chat_graph.py`)에 `ainvoke` 추가.

### 2. 그래프 노드 비동기화 (`engine/graph/chat_graph.py`)

- **`agent` 노드 → `async def`**: `ai = await m.ainvoke(state["messages"], config)`. 모델 호출이 async여야
  취소가 모델까지 전파된다(핵심).
- **`tools` 노드 → `async def`**: 도구 핸들러(`spec.handler`)는 sync·블로킹(MCP 등)일 수 있으므로
  `await run_in_threadpool(spec.handler, **args)`로 감싼다. 되묻기(INTERRUPT) 분기는 I/O 없음.
- **`approval_gate`**: 순수 로직(정책 평가 + `interrupt()`). sync 유지 가능 — LangGraph가 `astream`에서
  sync 노드를 실행기로 돌린다(빠르고 I/O 없어 무해). `interrupt()`는 async 그래프에서도 동작.
- ⚠️ 노드가 async면 **sync `.stream()`은 사용 불가**(async 노드를 동기 실행 못 함). chat 그래프의 모든
  구동을 `astream`으로 옮긴다(아래 §3·§6). gpts 그래프는 무관.
- `FakeToolCallingModel`(`fake_model.py`)에 `ainvoke` 추가(= `invoke` 위임) — 키 없는 로컬·테스트 불변.

### 3. 서비스 async 제너레이터화 (`domains/chat/service.py`)

`stream_message`·`regenerate`·`resume`·`resume_clarify`·`_run`을 **async 제너레이터**로 전환:
`async def` + `async for mode, chunk in _graph.astream(graph_input, config, stream_mode=["updates","messages"])`.

- **블로킹 사이드콜을 `run_in_threadpool`로 격리**(이벤트 루프 보호). 스트리밍 경로의 블로킹 지점:
  DB(`self.repo.*`, `get_storage().save_base64`), RAG(`RagService.rag_context`), 추출(`extract_text`),
  메모리(`memory.search/add`), 제목(`generate_title`), 스킬·프로젝트 조회. 토큰 루프 **자체**는 순수 async.
- **취소 시 부분 영속**(claude.ai식): `_run`에서 `except (asyncio.CancelledError, GeneratorExit)`로
  `display_parts`(미영속 토큰)를 `status="aborted"`로 저장 후 재전파. 취소 컨텍스트에서 저장이 잘려나가지
  않도록 **`shield`**하고 **별도 세션**(요청 세션 teardown 경합 회피, ADR-0025 패턴)으로 쓴다.
  `display_parts`가 비면(=노드 완료·이미 영속) 저장 안 함(중복 방지).
- 체크포인터: `InMemorySaver`는 async 메서드(`aget_tuple`/`aput`)를 구현하므로 `astream`에서 동작.
  다중 인스턴스 전환 시 `AsyncPostgresSaver`(ADR-0008 후속).

### 4. API 엔드포인트 async화 (`domains/chat/api.py`)

`send_message`·`regenerate`·`approvals`·`clarify`를 `async def`로, `StreamingResponse(async_gen)`을 직접
반환한다. **ADR-0025에서 넣은 `_abort_aware`(is_disconnected 폴링) 래퍼는 제거** — async 제너레이터는
Starlette가 연결 종료 시 네이티브로 취소(`aclose()`→`GeneratorExit`/`CancelledError`)하므로 폴링이 불필요.

### 5. DB 세션 — 단기 절충

도메인 repo는 **sync `Session`(SQLModel) 유지**하고, async 스트리밍 경로의 블로킹 DB 호출만
`run_in_threadpool`로 감싼다. 전면 `AsyncSession`(asyncpg) 전환은 모든 도메인 repo에 파급되므로
**별도 ADR로 분리**(후속). 스트리밍 경로의 DB 쓰기는 토큰당이 아니라 턴 경계(완료·중단·tool)라 빈도가
낮아 이 절충으로 충분하다.

### 6. 테스트

`tests/engine/test_clarification.py`를 `pytest.mark.asyncio` + `graph.astream`으로 전환(스텁 모델에
`ainvoke` 추가). 중단 취소 테스트 추가: async 제너레이터를 중간에 `aclose()`해 `aborted` 영속을 검증
(실 LLM 불필요, 결정적).

### 7. (선택) 명시적 stop 신호 — 보강

프록시/LB 환경에서 연결-종료 전파가 불확실한 경우를 대비해, 선택적으로 `POST …/stop`(세션별 취소
토큰)으로 진행 중 생성을 명시 취소하는 경로를 **보강**으로 둘 수 있다. async 네이티브 취소가 1차,
명시 stop은 belt-and-suspenders. 1차 범위 밖(필요 시 후속).

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| **sync 유지 + 명시적 stop 엔드포인트만**(협조적 취소 플래그) | 큰 리팩터 없이 중단은 되나, 모델 호출이 여전히 스레드풀 블로킹이라 **토큰/과금 즉시 중단이 불확실**하고 claude.ai식 네이티브 취소와 거리가 멀다. async의 보강책으로는 유효(§7). |
| **sync 유지 + nginx 튜닝**(keepalive·버퍼링 조정) | 근본(스레드풀 폴링 불안정) 미해결. 환경 의존·취약. |
| **전면 AsyncSession(asyncpg) 즉시 도입** | 모든 도메인 repo·테스트에 파급 — 범위 폭발. 스트리밍 경로 블로킹은 `run_in_threadpool`로 충분, 전면 전환은 별도 ADR. |
| **SSE 계약을 WebSocket으로 교체** | 양방향 인프라 선지불. 중단은 abort/취소로 충분(ADR-0008 동일 논리). |

## Consequences (결과)

**긍정**
- **확정적 중단**: 연결 종료 → 태스크 취소 → 모델 `astream` 중단 → **생성·과금 즉시 정지**. nginx 뒤에서도
  네이티브 취소라 신뢰 가능(ADR-0025 §5 한계 해소).
- 부분 영속이 취소 핸들러에서 확실히 실행(shield) → 새로고침 시 "중단됨" 일관.
- **SSE 계약·프론트 무변경** — 리스크 표면 최소. gpts·기타 sync 경로 불변.
- 동시성 향상(스레드풀 점유 감소) — 스트리밍이 이벤트 루프 네이티브.

**부정 / 리스크**
- **블로킹 콜 감사 필요**: 스트리밍 경로의 모든 블로킹(DB·RAG·추출·메모리·제목·스토리지)을 빠짐없이
  `run_in_threadpool`로 감싸야 한다. 누락 시 이벤트 루프 블로킹(정합성 아닌 성능 저하).
- provider별 async 토큰 스트리밍 편차 가능(ChatLiteLLM `ainvoke` 콜백 전파 — Azure 검증 필요).
- 취소-중 영속은 `shield` 필수(안 하면 저장이 취소돼 유실). 설계대로 처리.
- async 노드 도입으로 chat 그래프 sync `.stream()` 폐기 — 관련 테스트 astream 이전 필요.

**후속 작업**
- 전면 `AsyncSession`(asyncpg) 전환 — 별도 ADR(스트리밍 외 전역 성능).
- `AsyncPostgresSaver` 체크포인터(ADR-0008 후속)와 결합 — 다중 인스턴스·중단 세션 내구화.
- (선택) 명시적 `POST …/stop` 보강(§7), steer/barge-in(ADR-0025 후속).

## 전환 순서 (권장)

1. `LlmChatModel.ainvoke` + `ChatModel` 프로토콜 `ainvoke` + Fake `ainvoke`.
2. 그래프 노드 async화(`agent` await ainvoke, `tools` handler→threadpool).
3. 서비스 async 제너레이터(`astream`) + 블로킹 콜 `run_in_threadpool` + 취소 부분영속(shield·별도 세션).
4. API 엔드포인트 `async def` + `_abort_aware` 제거.
5. 테스트 astream 이전 + 취소 영속 테스트.
6. 배포 후 검증: 긴 답변 중 Stop → (a) 토큰 생성이 서버에서 즉시 멈추는지(로그·과금), (b) 새로고침 시
   부분이 `aborted`로 남는지, (c) nginx 경유에서도 동일한지.

## 검증 (2026-11-21, stg / docker-desktop)

- 일반 스트리밍·되묻기(ask_user)·되묻기 재개(실 gpt-4.1 답변) 정상 — 회귀 없음.
- **중단(nginx 경유)**: 긴 답변을 ~4s에 끊자 서버 생성이 멈추고 부분 응답이 `chat_message(status=aborted)`로
  영속됨(예: 1068자). ADR-0025 §5의 "nginx 경유 불안정" 한계가 **해소**됨 — async 네이티브 취소가
  모델 `astream`까지 전파되어 확정적으로 동작.
- 미해결/후속: 전면 `AsyncSession`(asyncpg), `AsyncPostgresSaver`(다중 인스턴스), 블로킹 사이드콜 중
  인라인으로 남겨둔 소형 DB 쓰기(턴 경계, 성능 영향 미미).
