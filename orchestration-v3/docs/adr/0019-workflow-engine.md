# ADR-0019: 워크플로우 — 노드 그래프 실행 엔진 + workflow 도메인

- 상태: Proposed
- 날짜: 2026-11-08
- 결정자: sehoon
- 관련: [ADR-0005](0005-ai-engine-layer.md) (engine 레이어 경계), [ADR-0010](0010-engine-llm-provider.md) (LlmConfig 주입), [ADR-0011](0011-chat-streaming-contract.md) (SSE 계약), [ADR-0012](0012-engine-rag.md) (rag 도메인 검색)

## Context (맥락)

web은 shadcn-admin 이식 시 **워크플로우 빌더 UI 전체**(`features/workflows/*` — React Flow 캔버스,
노드 팔레트 9종, 실행 패널, 스케줄/엔드포인트/웹훅 설정)와 API 클라이언트(`src/api/workflows.ts`)를
그대로 들여왔다. 클라이언트는 이미 **v3 계약**(`/api/v1/workflows/*`, `ApiResponse` unwrap)을 호출한다.
그러나 백엔드 `domains/workflow`는 `__init__.py`뿐이라 `/workflows` 화면 진입 시 첫 호출(`GET
/api/v1/workflows`)이 **404로 실패**한다 — 이것이 보고된 오류다.

V2(`orchestrator-server/src/workflow`, ~3,000 LOC)에 완성된 구현이 있다:

- **DAG 실행 엔진** — 노드/엣지를 위상 정렬, 선행 완료 노드를 `asyncio.gather`로 병렬 실행,
  condition 분기 skip 전파, 사이클 검출(Kahn).
- **노드 9종** — start·end·llm·condition·rag·http·code·tool·loop. 각자 `input_schema`/`output_schema`로
  프론트 팔레트 메타 제공.
- **템플릿 리졸버** — `{{input.x}}` / `{{nodes.<id>.output.y}}` 치환(ExecutionContext).
- **영속** — `WorkflowExecution`·`NodeExecution` 행에 실행 상태 기록.
- **트리거 3경로** — 동기 실행, SSE 스트림 실행, cron 스케줄(APScheduler), 웹훅 토큰, 동적 API 엔드포인트.

문제는 V2 엔진이 **DB 모델을 직접 import하고 실행 중 행을 commit**하며, RAG 노드가 `rag_service`(도메인)를
직접 호출한다는 점이다. 이는 v3의 단방향 경계(`domains → engine → core`, engine은 domains·FastAPI import
금지 — ADR-0005)를 정면으로 위반한다. 단순 복사가 불가능하므로 재배치 설계가 필요하다.

## Decision (결정)

### 1. 두 레이어로 분리 — `engine/workflow`(순수 실행) + `domains/workflow`(경계·영속·트리거)

```
engine/workflow/              # 순수 실행 능력 — DB·FastAPI·domains 미참조
├─ context.py                 # ExecutionContext + 템플릿 리졸버({{input}}·{{nodes.*}})
├─ planner.py                 # 노드/엣지 → 위상구조·사이클 검출(Kahn)
├─ runner.py                  # 병렬 DAG 러너 — 이벤트를 async-generator로 yield (DB 미접촉)
├─ events.py                  # NodeStart/Complete/Failed/Skipped/ExecutionComplete/Failed (Pydantic)
├─ ports.py                   # 도메인이 주입하는 포트 Protocol (rag_search 등)
├─ registry.py                # node_type → NodeClass, list_node_types()
└─ nodes/                     # base·start·end·llm·condition·rag·http·code·tool·loop

domains/workflow/             # HTTP 경계·관계형 영속·인가·오케스트레이션
├─ api.py                     # 라우터 (CRUD·node-types·executions·schedules·endpoints·webhook)
├─ service.py                 # 러너 이벤트 소비 → DB 영속 + SSE 포맷, 포트 주입, LlmConfig 해석
├─ repository.py              # Workflow·Execution·Schedule·Endpoint CRUD
├─ model.py                   # 5개 SQLModel 테이블 (아래)
├─ schema.py                  # Pydantic 요청/응답 (web workflows.ts 계약과 1:1)
└─ scheduler.py               # APScheduler 래퍼 (cron 트리거 — 인프라, 도메인 소유)
```

러너는 **DB·SSE 문자열을 모른다** — `ExecutionEvent` 객체를 async-generator로 흘린다. 도메인 서비스가
그 스트림을 소비하며 ① `NodeExecution`/`WorkflowExecution` 행을 commit, ② API용 `data: <json>\n\n` SSE로
직렬화한다. 이로써 영속·직렬화 정책이 도메인에 모이고 engine은 순수해진다.

### 2. engine 격리는 **포트 주입**으로 — RAG는 콜백, LLM은 LlmConfig

engine은 두 가지 외부 의존을 콜백/값으로 받는다(직접 import 금지):

- **RAG 노드** — 검색은 pgvector SQL(=`domains/rag` 소유, DB 접근)이다. engine은 `ports.RagSearch`
  Protocol만 정의하고, `domains/workflow.service`가 `domains/rag`를 호출하는 구현을 `ExecutionContext`에
  주입한다. engine→domains import가 생기지 않는다(engine은 주입된 callable만 호출).
- **LLM 노드** — 모델 선택은 `llm_resource` 테이블(DB). 도메인이 기본/요청 리소스를 `LlmConfig`로 해석해
  (ADR-0010 패턴, 기존 `_config_from_resource` 재사용) 컨텍스트에 주입하고, 노드는
  `engine/llm.build_chat_model(cfg)`로 조립한다(engine 내부 호출 — 허용). env 기본 모델 없음.

`code`·`http`·`condition`·`tool`·`start`·`end`·`loop` 노드는 외부 의존이 없어 그대로 순수 이식한다.
`import-linter` 계약(pyproject)에 `engine.workflow`도 포함해 경계를 CI로 강제한다.

### 3. 영속 — `llmonl` 5개 테이블 (`deploy/postgres/init.sql`)

V2 스키마를 계승(테이블명 동일):

| 테이블 | 용도 |
|--------|------|
| `workflow` | 정의(React Flow `{nodes,edges}` JSON) + 메타 + `webhook_token` |
| `workflow_execution` | 실행 1회 레코드(status·input·output·error) |
| `workflow_node_execution` | 실행 내 노드별 레코드 |
| `workflow_schedule` | cron 스케줄(APScheduler job_id = PK) |
| `workflow_endpoint` | 동적 API 경로 바인딩(`(path,method)` unique) |

ADR-0018에 따라 app-level `.env` 없이, 스케줄러 on/off 등 설정은 `api.env`에 추가한다. 모델은 SQLModel,
`ddl-auto` 없음 → `init.sql`에 `CREATE TABLE IF NOT EXISTS`로 직접 추가(다른 도메인과 동일).

### 4. API 계약 — web `src/api/workflows.ts`가 고정 소스, `/api/v1/workflows` prefix

web 클라이언트가 이미 확정한 엔드포인트를 그대로 구현한다(비스트리밍은 `ApiResponse[T]` 래핑 →
axios 인터셉터 자동 unwrap, 스트리밍은 raw SSE — ai_overview `/search`·chat과 동일 규칙):

- CRUD: `GET/POST /workflows`, `GET/PUT/DELETE /workflows/{id}`, `PATCH /workflows/{id}/publish`
- 팔레트: `GET /workflows/node-types`
- 실행: `POST /workflows/{id}/executions`(동기), `POST /workflows/{id}/executions/stream`(SSE),
  `GET /workflows/{id}/executions`, `GET /workflows/executions/{eid}`
- 스케줄: `GET/POST /workflows/{id}/schedules`, `PATCH/DELETE …/{sid}`
- 엔드포인트: `GET/POST /workflows/{id}/endpoints`, `PUT/DELETE …/{eid}`
- 웹훅: `PATCH /workflows/{id}/webhook?action=generate|revoke`

공개(미인증) 트리거는 별도 라우터로 `main.py`에 등록 — 웹훅 `POST /api/v1/webhooks/{token}`,
동적 엔드포인트 `ANY /api/v1/run/{path}`(artifact `public_router` 전례와 동일 패턴).

### 5. 단계적 이식 — MVP로 화면 복구 먼저, 트리거 고도화는 후속

- **Phase 1 (화면 복구 / MVP)**: 모델+`init.sql`, repository, CRUD, node-types, 동기+SSE 실행,
  실행 이력. 노드 start·end·llm·condition·code·http. → `/workflows` 목록·생성·편집·실행 E2E 동작.
- **Phase 2 (AI·반복 노드)**: rag(포트 주입)·tool·loop 노드.
- **Phase 3 (트리거 고도화)**: APScheduler 스케줄, 웹훅, 동적 엔드포인트 + lifespan 연동.

## Alternatives (대안)

- **엔진 전체를 `domains/workflow`에 두기** — engine 격리 부담은 없으나 ADR-0005의 "AI 실행 능력은
  engine" 원칙과 충돌하고, 재사용(향후 agent 도메인이 동일 노드 실행)이 막힌다. 기각.
- **V2 코드 그대로 복사(engine이 DB·domains 참조)** — 가장 빠르나 `import-linter`가 CI에서 막고,
  경계 drift가 누적된다. v3의 존재 이유(계약·경계 확정)에 반해 기각.
- **RAG 노드를 engine에서 `domains/rag` 직접 호출** — 경계 위반. 포트 주입으로 대체.
- **스케줄러를 engine에** — APScheduler·cron은 AI 연산이 아니라 인프라 트리거다. 도메인(또는 core)에 둔다.

## Consequences (결과)

- **긍정**: `/workflows` 화면 오류 해소. engine 순수성 유지로 노드 실행 능력을 agent 등 타 도메인이 재사용
  가능. 계약이 web에 이미 고정돼 프론트 변경 0. 영속·트리거 정책이 도메인에 응집.
- **부정/비용**: 포트 주입 레이어가 V2 대비 간접성을 추가(러너 이벤트 ↔ 도메인 소비자 분리). SSE 중
  sync SQLModel Session을 장기 보유하는 V2의 한계를 계승(별도 커넥션 관리는 후속 과제).
- **보안**: `code` 노드는 제한 빌트인 기반 `exec`로 샌드박스가 완전하지 않다(V2 계승). 신뢰 사용자 전용·
  관리자 경계 유지. 동적 엔드포인트/웹훅은 미발행 워크플로우에 대해 JWT를 요구한다.
- **후속**: 체크포인트/재개(chat과 유사), 노드 실행 병렬 커넥션 분리, `code` 샌드박스 강화, web
  `src/api/workflows.ts`의 `model` 문자열 → `llm_resource_id` 재매핑.
