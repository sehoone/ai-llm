# ADR-0007: LLM 관측(Observability)을 Langfuse에 위임

- 상태: Accepted
- 날짜: 2026-10-23
- 결정자: sehoon
- 관련: [ADR-0003](0003-single-python-backend.md) (단일 백엔드·언어무관 인프라 계승), [ADR-0005](0005-ai-engine-layer.md) (엔진 레이어·설정 주입 패턴)

## Context (맥락)

v3 deploy에는 이미 **Prometheus/Grafana/cAdvisor**가 있지만, 이들은 인프라·HTTP 레벨
지표(컨테이너 CPU/메모리, 요청 수·레이턴시)만 다룬다. **LLM 실행 레벨**(트레이스별 토큰/비용,
프롬프트·컴플리션 IO, generation 레이턴시, tool-call 체인, 세션·사용자 단위 추적, 품질 score)은
보이지 않는다. 이 축을 전용 도구로 채운다.

V2(`orchestration-v2`)는 Langfuse 3.x를 self-host로 운영했고(그대로 계승 가능한 언어무관 인프라 —
ADR-0003), LangChain `CallbackHandler`를 표준 LLM 호출과 LangGraph 실행에 붙여 트레이스했다.
트레이스 컨텍스트(`user_id`·`session_id`)는 `RunnableConfig.metadata`의
`langfuse_session_id`/`langfuse_user_id` 키로 전달했다.

v3의 제약:

- **엔진 격리(ADR-0005)** — LLM/그래프/에이전트 실행은 `engine/`에서 일어나고, engine은 `domains`·
  FastAPI를 import하면 안 된다(`import-linter` 강제). 그런데 트레이스에 붙일 컨텍스트는 HTTP 경계
  (domains)에서 나온다. 즉 **도메인이 값으로 주입**해야 한다(ADR-0005 §4 `ModelConfig` 주입과 동일).
- **프롬프트는 Git 자산(ADR-0005 §5)** — 프롬프트 관리는 `engine/prompts`가 소유한다.

## Decision (결정)

### 1. LLM 관측 도구로 Langfuse(self-host) 채택

V2 스택을 v3 deploy(격리 프로젝트 `orchestration-v3`)로 이식한다: `langfuse-web`·`langfuse-worker`
+ 의존성 `clickhouse`·`redis`·`minio`. Langfuse 전용 Postgres는 **기존 `db`(pgvector) 컨테이너의
별도 `langfuse` 데이터베이스**를 쓴다(앱 데이터 `mydb`와 분리). Prometheus/Grafana와 **보완 관계**
(인프라 지표 vs LLM 트레이스)이며 대체하지 않는다.

### 2. 계측은 `engine/observability/`에 둔다 (capability 아닌 횡단 모듈)

관측은 `llm`·`graph`·`agent`가 공통으로 쓰는 횡단 관심사라 특정 capability에 넣지 않고 형제 모듈로
신설한다. 엔진 경계 규칙(engine→domains·FastAPI 금지)은 그대로 지킨다.

```
engine/observability/
├─ context.py     # TraceContext 값 객체 (user_id, session_id, tags, extra)
├─ langfuse.py    # CallbackHandler 생성 + flush/shutdown, settings 가드
└─ runconfig.py   # TraceContext → RunnableConfig({callbacks, metadata})
```

### 3. 트레이스 컨텍스트는 도메인이 값으로 주입 (ADR-0005 §4 준수)

engine은 요청 상태를 읽지 않는다. 도메인 서비스가 인증 사용자·세션에서 `TraceContext`를 만들어
engine 호출에 넘긴다:

```
domains/chat/service.py
    trace = TraceContext(user_id=current.id, session_id=session.id, tags=["chat"])
    engine.llm.stream(model_config, messages, trace=trace)
        └─ run_config = engine.observability.build_run_config(trace)
              → {"callbacks":[CallbackHandler()],
                 "metadata":{"langfuse_session_id":..., "langfuse_user_id":..., "environment":...}}
        └─ llm.astream(messages, config=run_config)
```

### 4. 설정·수명주기

- `core/config.py`에 `LANGFUSE_PUBLIC_KEY`/`SECRET_KEY`/`HOST`/`ENABLED` + `langfuse_is_enabled`
  프로퍼티(키 존재 AND enabled). engine은 `core.config`만 의존(ADR-0005 허용 방향).
- **비활성 시 무해**: `langfuse_is_enabled`가 false면 `build_run_config`가 빈 config를 반환 →
  호출부에 분기 없음.
- **flush**: Langfuse SDK는 백그라운드로 전송하므로, FastAPI lifespan(core/main — HTTP 관심사)
  종료 훅에서 `engine.observability.shutdown()`을 호출해 flush한다(domains/core→engine, 허용 방향).

### 5. 경계: 프롬프트 관리는 Langfuse에 위임하지 않는다

Langfuse Prompt Management는 **쓰지 않는다**. 프롬프트는 ADR-0005 §5대로 `engine/prompts`의
Git 버전관리 자산으로 유지한다. Langfuse에는 **관측(트레이스·score)만** 위임한다.

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **Langfuse Cloud** | 인프라 0, 키만 설정 | 트레이스(프롬프트·IO)가 외부로 전송 → 사내 데이터 정책 제약. `HOST`로 전환 가능하게 코드는 중립 유지. |
| **OTel + Grafana Tempo/Loki** | 벤더 중립, 기존 Grafana 재사용 | LLM 전용 UX(토큰/비용·프롬프트 diff·세션·score)를 직접 재구현해야 함. |
| **콜백을 `engine/llm`에 직접 내장** | 모듈 1개 절약 | graph·agent도 공유 → 중복·결합. 횡단 모듈 분리가 깔끔. |
| **engine이 `llm_resource`·요청에서 컨텍스트 직접 조회** | 주입 1홉 제거 | engine→domains 역의존(ADR-0005 위반). |

## Consequences (결과)

**긍정**
- LLM 호출의 토큰·비용·IO·레이턴시·세션 추적 확보 — 기존 인프라 지표와 보완.
- 엔진 격리 유지: 계측은 engine 내부, 컨텍스트는 값 주입 → `import-linter` 계약 무위반.
- self-host로 트레이스 데이터가 사내에 남음(IdP 위임 환경과 정합).
- Cloud/self-host 전환이 `LANGFUSE_HOST`+키 설정만으로 가능.

**부정 / 리스크**
- 컨테이너 5개(clickhouse·redis·minio·worker·web) 추가 → 운영·리소스 비용.
- ClickHouse는 `config.xml`(단일노드 cluster 매크로·Keeper) 필요 — Langfuse v3 ReplicatedMergeTree 요구.
- Langfuse 전용 `langfuse` DB가 선행 생성돼야 함(앱 `mydb`와 별개) — postgres init 스크립트로 보장.
- 트레이스 컨텍스트 주입을 도메인이 빠뜨리면 트레이스에 세션/사용자가 안 붙음(계측 누락은 치명적
  오류는 아니나 리뷰 포인트).

**후속 작업**
- `engine/observability/` 스캐폴드(본 ADR와 함께) → 도메인 이식 시 각 서비스에서 `TraceContext` 주입.
- `core/config` LANGFUSE_* + `.env.example` 항목, `pyproject`에 `langfuse>=3`.
- deploy: Langfuse 스택 + `clickhouse/config.xml` + postgres `langfuse` DB init + `deploy/.env` 시크릿.
- (선택) web `평가(evaluation)` 기능을 Langfuse score로 백업하는 후속 ADR.
