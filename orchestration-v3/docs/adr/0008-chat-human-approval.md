# ADR-0008: 챗 사용자 승인 (Human-in-the-Loop)

- 상태: Accepted
- 날짜: 2026-10-28
- 결정자: sehoon
- 관련: [ADR-0005](0005-ai-engine-layer.md) (engine 레이어·주입 패턴), [ADR-0007](0007-llm-observability-langfuse.md) (관측), [ADR-0003](0003-single-python-backend.md) (인증 경계)

## Context (맥락)

챗이 단순 Q&A를 넘어 **도구(tool)를 호출**하기 시작하면, LLM이 부수효과·비가역·범위초과
동작을 자율 실행할 위험이 생긴다(메일 발송, 리소스 삭제, 외부 쓰기 API, 코드 실행 등).
"무엇을 사람이 승인해야 하는가"와 "그 승인을 아키텍처 어디서 처리하는가"를 도메인 이식 전에
확정해 둔다. 도메인(`chat`·`agent`)이 아직 빈 골격이라 지금이 경계를 세울 적기다(ADR-0005와 동일 논리).

제약:
- **단방향 레이어**(ADR-0005): "무엇이 위험한가"(정책)는 `engine`, "누가 승인하는가"(HTTP·영속·인가)는 `domains`.
  engine은 `domains`·FastAPI를 모른다 — 컨텍스트(역할·오버라이드)는 도메인이 **값으로 주입**(ADR-0005 §4·0007과 동일 패턴).
- 인증은 IdP 위임(ADR-0003) — 승인자 식별은 `get_current_user`가 준 로컬 `users.id`.

## Decision (결정)

### 1. 승인 단위는 "도구 호출", 판단은 3-티어

승인은 LLM 자유 텍스트가 아니라 **tool call(이름+인자)** 단위로 판정한다.

| 티어 | 의미 | 예 |
|------|------|----|
| `AUTO` | 읽기·안전 — 바로 실행 | RAG 검색, 내부 조회 |
| `CONFIRM` | 부수효과 — 실행 전 사용자 승인 | 메일 발송, 외부 쓰기, 코드 실행, 민감 데이터 접근, 고비용 |
| `BLOCK` | 노출 금지 — 챗에서 호출 불가 | 범위 밖 관리자 작업 |

`CONFIRM`의 변형: **edit-and-approve**(사용자가 인자 수정 후 승인). 파괴적·비가역 도구는
`allow_edit=False`로 수정을 막는다.

판단 소스 3겹(상향 우선):
1. **도구 기본 티어** — 레지스트리 메타데이터(`ToolSpec.risk`). 명시 안 하면 보수적으로 `CONFIRM`.
2. **역할/사용자 오버라이드** — `PolicyContext.auto_approve_tools`(도메인이 역할 기준으로 주입).
3. **런타임 술어** — 인자 기반 **승격만** 허용(`escalate_when`, 예: `amount > N`). 강등은 보안상 금지.

> 미등록 도구는 `BLOCK`(기본 거부). 승인은 **승격만** 가능하고 자동 강등은 없다.

### 2. 메커니즘 — LangGraph `interrupt()` + 체크포인터 재개

HITL 정석 패턴. 그래프가 `CONFIRM` 도구 직전 `approval_gate` 노드에서 `interrupt(payload)`로
일시중지하고 상태를 체크포인터에 영속한다. 사용자 응답이 오면 **같은 `thread_id`로 `Command(resume=...)` 재개**.

```
START → agent → (tool_calls?) ─no→ END
                     │yes
                     ▼
               approval_gate ──(CONFIRM 있으면 interrupt)──▶ [사용자 승인 대기]
                     │ (AUTO/승인된 호출만 통과, 거부/BLOCK은 ToolMessage로 치환)
                     ▼
                   tools → agent
```

- `thread_id = chat_session.id`. 체크포인터는 **현재 `InMemorySaver`**(인프로세스). 운영 다중
  인스턴스 전환 시 `langgraph-checkpoint-postgres`(`llmonl` 스키마)로 교체 — `core.config.chat_checkpointer`로 토글. (후속)

### 3. 레이어 배치

```
domains/chat/     # HTTP 경계 + 영속 + 인가
  api.py          #   POST /sessions/{id}/messages (SSE), POST /sessions/{id}/approvals (SSE 재개)
  service.py      #   그래프 구동, interrupt↔SSE 변환, 승인 검증·재개, 메시지/승인 영속
  repository.py   #   chat_session · chat_message · chat_approval
  model.py schema.py
engine/agent/
  registry.py     # ToolSpec(risk·allow_edit·escalate_when) + ToolRegistry
  policy.py       # ToolCall + PolicyContext → PolicyResult(ALLOW|CONFIRM|BLOCK)  ← 순수·테스트가능
engine/graph/
  chat_graph.py   # agent·approval_gate·tools 노드, interrupt() 지점 (model은 주입)
  checkpointer.py # InMemory(기본) | postgres(후속)
core/config.py    # chat_approval_ttl_seconds · chat_checkpointer
```

engine은 `interrupt()`로 **"승인 필요" 신호만** 올린다. HTTP 이벤트화·DB 영속·인가·만료는
`domains/chat`가 소유한다. `PolicyContext`(역할·오버라이드)는 도메인이 생성해 config로 주입 —
engine은 `User`·요청을 모른다(ADR-0005 §4).

### 4. HTTP 흐름 (SSE는 단방향 → "중단 후 재개")

1. `POST /sessions/{id}/messages` → 그래프 `stream`. `CONFIRM` 만나면 스트림이
   `event: approval_required`(group_key + 요청들) 한 건 내고 **종료**. 각 요청은 `chat_approval`(PENDING, TTL)로 영속.
2. 프론트가 승인 카드 렌더 → `POST /sessions/{id}/approvals {decisions:[{tool_call_id, approved, args?}]}`.
3. 서버는 소유자·PENDING·미만료 검증 후 결정 기록(+Langfuse), `Command(resume=…)`로 **이어서 SSE 재개**.

SSE가 서버→클라 단방향이라 승인 입력은 어차피 별도 POST가 필요하다. 중단 시 스트림을 닫고
승인 POST가 새 스트림으로 이어받는 것이 상태관리상 가장 단순하다. `thread_id` 체크포인트가
보존되므로 연결이 끊겨도 안전하다.

### 5. 보안·감사·만료

- **인가**: 승인 POST는 thread(세션) **소유자 또는 관리자**만. `tool_call_id`가 그 세션의 PENDING 행과 일치해야 함(재생공격 차단).
- **TTL**: `chat_approval.expires_at` 경과 → 승인 불가, `EXPIRED`로 마킹하고 해당 호출은 거부로 재개.
- **기본 거부**: resume 결정 맵에 빠진 PENDING 요청은 **거부**로 처리(fail-safe). BLOCK·미등록 도구도 거부.
- **감사**: `chat_approval`에 요청·결정·결정자·시각 보존(체크포인트와 **분리** — 체크포인트는 재개용, 이 테이블은 이력·재생방지·UI용). 결정은 Langfuse 이벤트/score로도 기록(ADR-0007, 컨텍스트 값 주입).

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| **티어 없이 "모든 tool call 승인"** | UX 마비(검색마다 승인). 읽기·안전 작업은 AUTO로 흘려야 한다. |
| **프롬프트로 "위험하면 물어봐" 지시** | LLM 자율 판단에 안전을 의존 — 비결정적·우회 가능. 정책은 코드로 강제해야 함. |
| **승인 정책을 domain에 두기** | 도구 위험도는 AI 능력의 속성 → engine 소유가 응집적. domain은 인가/영속만. |
| **단방향 SSE에서 승인까지 처리(WebSocket 전환)** | 양방향 인프라 선지불. 입력은 멱등 POST로 충분, 체크포인트가 상태를 보존. |
| **Postgres 체크포인터 즉시 도입** | 의존성(`langgraph-checkpoint-postgres`) 선지불. 단일 인스턴스 골격엔 InMemory로 충분, config 토글로 전환 경로만 확보. |

## Consequences (결과)

**긍정**
- 안전이 **코드로 강제**됨(프롬프트 의존 제거). 티어로 UX와 안전 균형.
- 정책(engine)·승인(domain) 분리로 재사용(`agent` 도메인도 동일 정책 사용) + 레이어 규칙 유지.
- `interrupt`/체크포인트로 중단·재개가 멱등·내구적.

**부정 / 리스크**
- InMemory 체크포인터는 **단일 인스턴스 전제** — 스케일아웃 전 Postgres saver 전환 필요(후속, config 토글 준비됨).
- 토큰 스트리밍은 현재 노드 단위(`updates`) — 세밀한 토큰 SSE는 후속(`stream_mode="messages"`).
- 모델 노드는 `engine/llm` 이식 전까지 주입 seam(로컬 데모용 `FakeToolCallingModel`) — 실모델 교체 필요.

**후속 작업**
- `langgraph-checkpoint-postgres` 도입 + `chat_checkpointer="postgres"` 구현(`llmonl` 스키마).
- `engine/llm` 이식 후 `FakeToolCallingModel` → 실제 tool-calling 모델로 교체(`llm_resource` 주입).
- 토큰 단위 SSE(`messages` 모드), 승인 만료 스윕 잡, `agent` 도메인에 동일 정책 적용.
