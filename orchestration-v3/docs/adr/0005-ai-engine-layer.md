# ADR-0005: AI 엔진 레이어 분리 (domains ↔ engine)

- 상태: Accepted
- 날짜: 2026-10-17
- 결정자: sehoon
- 관련: [ADR-0003](0003-single-python-backend.md) (단일 백엔드), [ADR-0004](0004-apps-packages-monorepo-layout.md) (후속으로 지목)

## Context (맥락)

ADR-0004는 "AI 실행 엔진을 HTTP 도메인에서 분리"하는 패턴을 후속 과제로 남겼다. 조사 근거:

- **Dify** — 일반 CRUD는 `controllers/services/models`(레이어)지만, AI 복잡도는 전부 별도
  `core/` 트리에 **능력(capability) 단위**(agent·rag·workflow·model_runtime·prompt·tools·memory)로 격리.
- **n8n** — 실행 엔진(`workflow`+`core`)이 서버(`cli`)·UI와 독립 패키지.
- **wassim249 / vstorm-co 템플릿** — `core/langgraph`+`core/prompts`, 전용 `agents/`·`rag/` 모듈.
- 공통점: **프롬프트·그래프·툴·모델런타임·ingestion은 요청/응답 도메인 슬라이스 안에 두지 않는다.**

현재 V3는 `apps/api/src/domains/{chat,rag,agent,workflow,meeting}`을 `user`·`api_key`와 **동급
수직 슬라이스(api·service·repository·schema)로 평탄화**했다. 두 가지 문제:

1. **4분할에 안 맞는 관심사** — 프롬프트 템플릿·LangGraph 그래프·tool 정의·청킹/임베딩은
   `api/service/repository/schema` 어디에도 자연스럽게 안 들어간다.
2. **교차 도메인 중복** — LLM 호출은 chat·agent·rag(생성 단계)가 공유하고, 프롬프트/메모리도
   여러 도메인이 쓴다. 도메인마다 복제하면 drift(ADR-0003이 없애려던 바로 그 문제)가 재발한다.

도메인들이 **아직 빈 골격**이라, 로직 이식 전인 **지금이 경계를 세울 적기**다.

## Decision (결정)

### 1. `engine/`를 `domains/`·`core/`와 나란한 능력 레이어로 신설

```
apps/api/src/
├─ domains/        # HTTP 경계 — api·service·schema(+repository). 얇게 유지.
│                  # chat rag agent workflow meeting user api_key llm_resource auth
├─ engine/         # AI 실행 능력 — HTTP·FastAPI 비의존
│  ├─ llm/         # 모델 호출 추상화 (provider·chat·stream). 프로바이더 중립.
│  ├─ prompts/     # 프롬프트 템플릿 (Git 버전관리, 로직과 분리) + 로더
│  ├─ rag/         # ingestion·chunking·embedding·retrieval + 벡터스토어 어댑터
│  ├─ agent/       # tool 정의·레지스트리·tool calling 실행
│  ├─ graph/       # LangGraph 워크플로 그래프·노드 정의
│  ├─ memory/      # 대화 메모리
│  └─ transcription/  # 음성 전사 (Whisper 등) — meeting용
└─ core/           # config·db·security(OIDC)·DI·미들웨어
```

### 2. 의존 방향 규칙 (단방향, 강제)

```
domains  ──>  engine  ──>  core(config·db)
   │                         ▲
   └─────────────────────────┘  (domains는 core도 직접 사용)
```

- **engine은 `domains`를 import하지 않는다.** (역방향 금지 — 순환·결합 차단)
- **engine은 FastAPI·HTTP를 모른다.** 라우팅·요청/응답 스키마·인증은 전부 `domains`/`core`.
- engine은 `core.config`(설정)와 `core.db`(벡터 연산용 세션)만 의존한다.
- **관계형 도메인 테이블 CRUD는 `domains/<d>/repository.py`** 가 소유(chat 세션·메시지, meeting 레코드 등).
  **벡터스토어(pgvector) 접근은 `engine/rag`** 가 AI 관심사로서 소유.

### 3. 도메인 ↔ 엔진 매핑

| 도메인 (HTTP) | 사용하는 엔진 능력 | 도메인이 소유 |
|---------------|-------------------|---------------|
| `chat`     | `llm` · `prompts` · `memory` | 세션·메시지 영속화, SSE 응답 |
| `rag`      | `rag`(ingestion·retrieval) · `llm`(생성) · `prompts` | 문서 메타 영속화, 업로드 API |
| `agent`    | `agent`(tools) · `llm` · `prompts` | 실행 요청·결과 영속화 |
| `workflow` | `graph` · `llm` | DAG 정의·실행 이력 |
| `meeting`  | `transcription` · `llm`(요약) · `prompts` | 업로드·녹취 레코드 |

패턴: **도메인 서비스가 유스케이스를 조율하고, 실제 AI 연산은 engine 호출로 위임**한다.
예) `ChatService.send()` → `engine.llm.stream(prompt=engine.prompts.render("chat.system", ...))`.

### 4. `llm_resource` 연동 — engine은 설정을 "주입받는다"

`llm_resource` 도메인은 모델 설정(DB)을 소유한다. engine은 이 테이블을 읽지 않는다(그러면
engine→domain 역의존 발생). 대신 **도메인 서비스가 설정을 해석해 engine에 값으로 전달**한다:

```
llm_resource.repository → ModelConfig(값 객체) → engine.llm.chat(config, messages)
```

engine은 프로바이더 중립 인터페이스(`LLMProvider`)만 알고, 자격증명·엔드포인트는 호출 시 주입된다.

### 5. 프롬프트는 Git 버전관리·로직 분리

- `engine/prompts/<domain>/<name>.jinja` 템플릿 + 얇은 로더(`render(id, **vars)`).
- 프롬프트는 **코드가 아닌 자산** — 로직과 분리해 변경·리뷰·(향후)A·B가 재배포 없이 가능하도록.

### 6. 위치: 지금은 앱 내부, 트리거 시 `packages/engine`으로 승격

- 현재 소비자는 `apps/api` 하나뿐 → **`apps/api/src/engine/`에 둔다** (별도 패키징 오버헤드 회피, YAGNI).
- **승격 트리거**: ADR-0004가 예고한 `apps/worker`가 engine 능력(전사·ingestion)을 소비하게 되면,
  `engine/`을 **`packages/engine`(공유 라이브러리)로 승격**한다. 위 의존 규칙(engine의 domains·HTTP
  비의존)을 처음부터 지키므로 승격 비용은 "디렉토리 이동 + pyproject 분리"로 제한된다.

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **도메인 슬라이스 유지** (현행 / fastapi-best-practices 순정) | 구조 단일, 학습 비용 0 | 프롬프트·그래프·툴이 4분할에 안 맞고, LLM 호출 교차 중복→drift 재발. |
| **Dify식 대형 `core/` 능력 트리** (+plugin·mcp·datasource·rbac) | 제품급 확장성 | 사내 bounded 플랫폼엔 과함(YAGNI). plugin·멀티벡터스토어 추상화 불필요. |
| **처음부터 `packages/engine`** | worker 공유 즉시 대응 | 소비자 1개인데 패키징·설치 오버헤드 선지불. 트리거 기반 승격으로 대체. |
| **`engine/`를 둘로(순수 compute vs IO)** | 테스트 경계 선명 | 초기 과분할. 능력별 모듈 내부에서 자연히 갈리면 그때 분리. |

## Consequences (결과)

**긍정**
- **AI 관심사 응집** — 프롬프트·그래프·툴·모델런타임이 한곳에, 도메인은 얇은 HTTP 경계로 유지.
- **교차 도메인 재사용** — `llm`·`prompts`를 chat·agent·rag가 공유, 복제·drift 차단(ADR-0003 정신 연장).
- **테스트 용이** — engine은 HTTP·DB(관계형) 비의존이라 순수 단위 테스트 가능.
- **worker 확장 경로 확보** — 승격 트리거로 `packages/engine` 전환이 저비용.

**부정 / 리스크**
- 레이어 추가로 **초기 간접화** — "도메인 서비스 → engine 호출" 1홉이 늘어난다(얇게 유지하면 수용 가능).
- `rag`의 벡터스토어 접근이 engine, 관계형 메타가 domain으로 **갈려 트랜잭션 경계 주의** 필요.
- 경계 규칙(engine→domains 금지)은 **리뷰/도구로 강제**하지 않으면 침식될 수 있음(아래 후속).

**후속 작업**
- `engine/` 골격 스캐폴딩(`llm`·`prompts`·`rag`·`agent`·`graph`·`memory`·`transcription` + 각 `__init__.py`·README).
- `domains/README.md`에 "AI 도메인은 로직을 engine에 위임" 규칙 명시, `CLAUDE.md` 규칙 보강.
- import 경계 린트(예: ruff `flake8-tidy-imports` banned-api / import-linter)로 engine→domains 역의존 금지 강제.
- `apps/worker` 도입 시 본 ADR의 승격 트리거에 따라 `packages/engine` 전환 ADR 작성.
