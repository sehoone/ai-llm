# ADR-0025: 챗 되묻기·사람 개입 (Clarification & Interrupt)

- 상태: Accepted (2026-11-21 구현·stg 실증. 중단 내구화 §5는 [ADR-0026](0026-chat-async-streaming.md)로 완성)
- 날짜: 2026-11-21
- 결정자: sehoon
- 관련: [ADR-0008](0008-chat-human-approval.md)(HITL 승인·interrupt/재개), [ADR-0011](0011-chat-streaming-contract.md)(스트리밍 계약), [ADR-0005](0005-ai-engine-layer.md)(engine 경계), [ADR-0020](0020-user-portal-frontend.md)(thread-rev 재생성)
- 로드맵: [portal-roadmap](../portal-roadmap.md) Phase 3(능력 확장)·Phase 1(스트리밍 제어) 연장

## Context (맥락)

챗은 이미 **중단→사람 입력→재개** 루프를 가지고 있다. ADR-0008이 CONFIRM 도구에서
LangGraph `interrupt()`로 멈추고 `POST /approvals`로 재개하며, ADR-0011이 그 위에 토큰 스트리밍을
얹었다. 클라이언트 `stop()`(`use-chat.ts` → `AbortController`)도 있다.

그러나 "챗 완성도" 관점에서 **사람↔AI 양방향 개입**에 세 가지 결핍이 있다:

1. **되묻기(clarification) 부재** — 요청이 모호하거나 정보가 부족해도 모델이 추측해 답한다.
   사용자가 방향을 바로잡는 유일한 수단은 "또 한 번 전송"뿐 — 모델이 **턴 중간에 되물을** 수단이 없다.
2. **중단(stop)이 불완전** — 클라이언트 `fetch`만 abort한다. 서버 그래프는 계속 생성하고(토큰·비용 낭비),
   부분 응답은 DB에 **영속되지 않아** 새로고침하면 사라진다. 중단된 메시지의 상태 구분도 없다.
3. (약) 생성 중 **끼어들어 조종(steer)** 불가 — 양방향 채널이 없다.

**기회**: ADR-0008의 `interrupt()`/체크포인트 재개 기계는 이미 "멈춰서 사람을 기다렸다가 이어간다"를
한다. 되묻기는 이 기계의 **두 번째 사용처**일 뿐 — 그래프 토폴로지를 새로 만들 필요가 없다.

제약:
- **단방향 레이어**(ADR-0005): "되물을지 판단 + 되묻기 능력"은 `engine`, "HTTP·영속·인가"는 `domains/chat`.
- **안전 vs UX 구분**(ADR-0008): 승인은 *안전*이라 **코드로 강제**(프롬프트 의존 거부)했다. 되묻기는
  *UX*다 — 무엇을 되물을지는 맥락 의존적이라 **모델 주도(tool call)**가 적절하다. 이 경계를 명시한다.
- **SSE 단방향**: 승인과 동일하게 "중단 후 재개"(ADR-0008 §4)를 재사용한다. 입력은 멱등 POST.

## Decision (결정)

### 1. 인터럽트를 일반화한다 — 승인은 그중 한 종류

`interrupt()` 페이로드에 이미 있는 `type` 판별자를 **계약의 1급 요소**로 올린다. 현행 `approval_required`에
신규 `clarification_required`를 더한다. 재개 값도 `type`별로 해석한다. engine은 "사람이 필요하다"는
신호만 올리고, HTTP 이벤트화·영속·인가는 domains가 소유한다(ADR-0008 §3 불변).

```
interrupt 종류 (engine/graph):
  approval_required      — 외부 도구가 CONFIRM 티어 (ADR-0008, 안전)
  clarification_required — 모델이 ask_user 호출 (본 ADR, UX)
```

### 2. 되묻기 = 내장 `ask_user` 도구 (모델 주도)

되묻기를 **별도 그래프 분기**가 아니라 **내장 도구**로 모델에 노출한다 — 기존 tool-call·gate·resume
경로를 그대로 재사용하기 위함이며, 업계 표준(tool use)과도 정렬된다.

- **`ToolSpec` 확장**(`engine/agent/registry.py`): 도구 종류를 구분하는 `kind: ToolKind` 추가.
  ```
  class ToolKind(StrEnum):
      EXTERNAL  = "EXTERNAL"   # 외부 부수효과 도구 — 정책(AUTO/CONFIRM/BLOCK) 평가 대상
      INTERRUPT = "INTERRUPT"  # 사람 입력 수집용 — 실행 대신 interrupt 발생
  ```
  `ask_user`는 `kind=INTERRUPT`, `risk=AUTO`(부수효과 없음 — 승인 대상이 아님). 핸들러는 없다
  (실행되지 않고 사용자 답변이 결과를 대체).

- **도구 시그니처**: `ask_user(question: str, options?: list[{value,label}], allow_free_text: bool = True)`.
  모델이 질문과 (선택적) 보기를 **구조화**해 생성한다.

- **시스템 프롬프트 가이드**(`engine/prompts`): "핵심 정보(대상·기간·형식 등)가 빠졌으면 **추측하지 말고
  `ask_user`로 되물어라**." 단 **강제가 아니다**(UX이므로) — 안전 결정이 아니기에 ADR-0008의 "프롬프트
  의존 금지"와 충돌하지 않는다.

### 3. 그래프 — `gate`의 분기 확장 (토폴로지 불변)

`approval_gate`가 마지막 AIMessage의 tool_calls를 **종류로 분류**한다(`engine/graph/chat_graph.py`):

```
agent → route(tool_calls?) ─no→ END
                │yes
                ▼
              gate ┬─ INTERRUPT(ask_user) 있음 → interrupt(clarification_required)
                   │                              └ resume(answer) → ToolMessage(ask_user=answer) → agent
                   ├─ EXTERNAL CONFIRM 있음      → interrupt(approval_required)   [ADR-0008]
                   └─ 그 외(AUTO/승인됨)          → tools → agent
```

- **우선순위**: 한 턴에 `ask_user`와 외부 도구가 섞이면 **되묻기 우선** — `ask_user`만 interrupt로 처리하고
  나머지 호출은 이번 라운드에서 버린다(`ToolMessage`로 "되묻기 대기로 보류" 치환). 사용자 답변 후 모델이
  다음 라운드에서 재계획한다. (모델에는 `ask_user` 단독 호출을 기대하도록 프롬프트.)
- 재개 값: `{tool_call_id: {"text"?: str, "value"?: str}}` → `ask_user` 호출의 `ToolMessage` content로
  주입. 승인(approved/args)과 **구조만 다른 동일 resume 메커니즘**.

### 4. HTTP 계약 (ADR-0011에 가산)

**신규 SSE 이벤트** 1종 (§1 집합에 추가):

| event | data | 의미 |
|-------|------|------|
| `clarification_required` | `{tool_call_id, question, options?[{value,label}], allow_free_text}` | 모델이 되묻고 스트림 종료. |

**신규 재개 엔드포인트** (ADR-0008 `/approvals`와 대칭):

```
POST /api/v1/chat/sessions/{id}/clarify
  { tool_call_id: str, answer: { text?: str, value?: str } }
→ Command(resume=…) 로 같은 SSE 계약(ADR-0011) 이어서 재개
```

- **영속**: 되묻기 질문/답변은 대화 흐름의 일부다 → `ask_user` 호출은 assistant의 `tool_calls`로,
  답변은 `role="tool"` ChatMessage로 **기존 메시지 영속을 그대로 재사용**한다. 승인(ADR-0008)과 달리
  **별도 감사 테이블(`chat_approval`)은 만들지 않는다** — 안전 결정이 아니라 대화 내용이기 때문.
- **공통 resume 코어**: `/approvals`와 `/clarify`는 서비스 내부에서 `_resume(thread, resume_value)`
  코어를 공유한다. 표면 엔드포인트는 선례와의 대칭성 때문에 분리 유지(아래 대안 참고).

### 5. 사람 개입(중단)을 내구적으로 — `stop` 강화

현행 `stop()`은 클라이언트 abort뿐이라 서버가 계속 돌고 부분 응답이 소실된다. 다음을 더한다:

- **서버 측 중단 감지·부분 영속**: `domains/chat/service.stream_message` 제너레이터가 `GeneratorExit`
  (클라 연결 종료) 또는 `await request.is_disconnected()`를 감지하면, 그때까지 누적한 assistant 토큰을
  `chat_message(status="aborted")`로 저장하고 그래프 astream을 중단한다. → 새로고침해도 "중단됨" 유지,
  서버 생성·비용 낭비 차단.
- **`chat_message.status` 컬럼 신규**(`model.py`): `"complete" | "aborted"`, 기본 `"complete"`.
  schema는 수동 관리이므로 `deploy/postgres`에 멱등 `ALTER TABLE … ADD COLUMN IF NOT EXISTS` 추가.
- **스레드 일관성 경계(명문화)**: 토큰 스트리밍(`messages` 모드)에서 중단은 노드 미완 → 체크포인트
  **미커밋**. 즉 부분 assistant는 **DB에는 "표시용"으로 남지만 그래프 스레드 맥락에는 없다**. 사용자가
  "이어서"를 원하면 재전송이 아니라 **재생성(ADR-0020 thread-rev 포크)**으로 처리한다. UI 문구로 이
  구분을 완화한다("중단됨 — 재생성").

> **구현 노트 (2026-11-21)**: 클라이언트 측(부분 응답 보존 + "중단됨" 배지)은 안정적으로 동작한다.
> 서버 측 중단 감지는 API 레이어 async 래퍼가 `request.is_disconnected()`를 폴링하고, 끊기면 sync
> 제너레이터를 `close()`해 `GeneratorExit` 핸들러(별도 세션으로 부분 영속)를 발화시킨다. **그러나
> threadpool 기반 sync 스트리밍 + nginx keepalive 조합에서 disconnect 감지가 지연·누락될 수 있어
> 서버 측 영속은 best-effort**다(api 직결 시엔 재현 가능, nginx 경유 시 불안정). 확정적 중단·영속은
> LLM astream 기반 **async 스트리밍 전환**이 필요 — 후속 과제. 미발화 시 생성이 완료되어 `complete`로
> 저장되므로 데이터 손실은 없다(토큰 절감만 미보장).

### (후속) 생성 중 조종 (steer / barge-in)

생성 도중 사용자 추가 입력을 큐잉했다가 다음 스텝에 주입하는 "조종"은 **양방향 채널**(현 단방향 SSE
한계)을 요구한다. 멱등 POST로 충분한 clarify·stop과 성격이 달라 **범위 밖**으로 둔다 — 별도 ADR 후보.

### 6. 레이어 배치 (ADR-0005)

```
engine/agent/registry.py   # ToolKind 추가 + ask_user ToolSpec(INTERRUPT·AUTO)
engine/graph/chat_graph.py # gate 분기: INTERRUPT → clarification interrupt
engine/prompts/            # ask_user 사용 가이드(되묻기 권장 — 강제 아님)
domains/chat/service.py    # clarification interrupt ↔ SSE, _resume 코어 + /clarify, 중단 부분영속
domains/chat/api.py        # POST /sessions/{id}/clarify
domains/chat/model.py      # chat_message.status
deploy/postgres/           # status 컬럼 멱등 ALTER
apps/portal/src/
  api/chat.ts              # onClarificationRequired 콜백 + submitClarify()
  stores/chat-store.ts     # pendingClarification 상태
  components/chat/clarification-card.tsx   # 질문 + 보기 칩 + 자유입력
  components/chat/message-actions.tsx      # 중단 메시지에 재생성 액션
  hooks/use-chat.ts        # submitClarification + 중단 상태 반영
```

engine은 `interrupt()`로 신호만, domains가 이벤트화·영속·인가·재개를 소유한다(ADR-0008 §3과 동일 패턴).

### 7. 보안·만료·엣지

- **인가**: `/clarify` 재개도 세션 **소유자 또는 관리자**만(ADR-0008 §5 동일). `tool_call_id`가 현재
  중단된 thread의 pending interrupt와 일치해야 한다 — **체크포인트가 권위**(재생공격 차단).
- **만료**: 되묻기는 승인만큼 민감하지 않아 별도 TTL 테이블을 두지 않고 **체크포인트 존재 여부**로 판정
  한다(InMemory 재시작·thread-rev 포크 시 자연 무효화).
- **중복 가드**: `pendingClarification` 동안 새 `send` 차단(기존 `pendingApproval`과 동일하게
  store·use-chat에서). 세션 전환·새 대화 시 클리어.

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| **프롬프트만으로 "모호하면 되물어"** | 질문·보기가 구조화되지 않아 선택지 UI·재개 매칭 불가. 비결정적. 도구로 구조화한다. |
| **되묻기를 승인 interrupt로 재사용**(tier=CONFIRM) | "승인"과 "질문"의 의미가 섞인다. 감사 테이블·tier·edit 개념이 되묻기에 부적합. 별 `type`이 깔끔. |
| **통합 `/resume` 단일 엔드포인트** | ADR-0008 `/approvals` 선례와의 대칭이 깨진다. 내부 `_resume` 코어만 공유하고 표면은 대칭 유지(여지는 남겨둠 — 인터럽트 종류가 더 늘면 재검토). |
| **되묻기 없이 사용자가 재전송** | 턴 중간 질문 불가 → 맥락 유지·보기 제시 UX 상실. |
| **중단을 클라이언트만**(현행 유지) | 부분 응답 소실 + 서버 생성 낭비. 서버 감지로 비용·내구성 개선. |
| **WebSocket 양방향 전환**(steer까지 한 번에) | 양방향 인프라 선지불. clarify·stop은 멱등 POST + 체크포인트로 충분(ADR-0008 동일 논리). steer만 후속 분리. |

## Consequences (결과)

**긍정**
- 되묻기·중단 모두 **기존 interrupt/resume 위 가산** — 그래프 토폴로지 변경 최소, 계약 재사용.
- **안전(승인)과 UX(되묻기)의 의미 분리** 유지 — 승인은 코드 강제, 되묻기는 모델 주도. 업계 tool-use 정렬.
- 중단이 내구적(부분 영속 + 상태 구분) → "클로드급" 스트리밍 제어 완성(portal-roadmap Phase 1 연장).

**부정 / 리스크**
- `ask_user`와 외부 도구가 **혼재한 턴**은 엣지 — 1차는 되묻기 우선·나머지 보류(다음 라운드 재계획).
- 중단 부분 영속은 **"표시용"**(체크포인트 미포함)이라 사용자의 "이어쓰기" 기대와 괴리 가능 → UI 문구로 완화.
- **InMemory 체크포인터**(ADR-0008 후속) 전제 여전 — 서버 재시작 시 중단·되묻기 세션 재개 불가.

**후속 작업**
- `langgraph-checkpoint-postgres` 전환(ADR-0008 후속)과 함께 중단·clarify 세션 **내구화**.
- 생성 중 **조종(steer/barge-in)** — 양방향 채널 별도 ADR.
- 되묻기 **폼형 확장**(여러 필드를 한 번에 수집), 다중 질문 배치.
