# ADR-0028: LangGraph Postgres 체크포인터 (중단·HITL 세션 내구화)

- 상태: Accepted (2026-11-21 구현·stg 실증 — 아래 "검증" 참고)
- 날짜: 2026-11-21
- 결정자: sehoon
- 관련: [ADR-0008](0008-chat-human-approval.md)(interrupt/재개 — 후속), [ADR-0026](0026-chat-async-streaming.md)(async 그래프), [ADR-0025](0025-chat-clarification-and-interrupt.md)(되묻기·중단), [ADR-0018](0018-env-config-layout.md)(env)

## Context (맥락)

HITL 승인(ADR-0008)·되묻기(ADR-0025)·중단(ADR-0026)은 모두 LangGraph **체크포인트**에 의존해 중단 지점을
저장하고 재개한다. 그런데 현재 체크포인터는 `InMemorySaver`(인프로세스) — `engine/graph/checkpointer.py`의
`build_checkpointer("postgres")`는 `NotImplementedError`다.

결과 한계:
- **서버 재시작** 시 진행 중이던 승인/되묻기 대기가 **전부 소실** → `/approvals`·`/clarify` 재개 불가.
- **다중 인스턴스**(스케일아웃) 시 재개 요청이 체크포인트를 가진 인스턴스로 라우팅돼야만 동작 → 사실상 단일 인스턴스 전제.

ADR-0008은 이미 "스케일아웃 전 Postgres saver 전환"을 후속으로 명시했고, config 토글(`chat_checkpointer:
"memory"|"postgres"`)과 팩토리 seam을 준비해 두었다. ADR-0026으로 그래프가 **async**가 됐으니, 짝이 되는
**AsyncPostgresSaver**를 연결할 적기다.

제약:
- DB 좌표는 `settings`(ADR-0018)에서 온다. 드라이버는 **psycopg3**(`postgresql+psycopg://`) — 별도 asyncpg 불필요.
- 스키마는 `llmonl`(pgvector 공유). 체크포인트 테이블도 여기에 둔다.
- 엔진 경계(ADR-0005): 팩토리·saver는 `engine/graph`, 라이프사이클 배선은 `domains`/`main`.

## Decision (결정)

`chat_checkpointer="postgres"`일 때 **`AsyncPostgresSaver`**(langgraph-checkpoint-postgres)를 **psycopg
AsyncConnectionPool** 위에 올려 체크포인트를 `llmonl`에 영속한다. 기본값은 `memory` 유지(로컬·CI·테스트 불변).

### 1. 의존성 + 팩토리 (`engine/graph`)

- `pyproject.toml`에 `langgraph-checkpoint-postgres` 추가(psycopg는 이미 `psycopg[binary,pool]` 보유).
- `checkpointer.py`: `build_checkpointer`를 **async 라이프사이클 객체**로 확장. postgres 경로는 풀 생성·
  `setup()`(테이블·마이그레이션)·`close()`를 캡슐화한 핸들을 반환한다.
  ```
  pool = AsyncConnectionPool(
      conninfo,  # settings에서 조립: postgresql://user:pass@host:port/db (SQLAlchemy URL 아님 — psycopg DSN)
      open=False,
      kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0,
              "options": "-csearch_path=llmonl,public"},  # core/db와 동일 — 테이블을 llmonl에
  )
  await pool.open()
  saver = AsyncPostgresSaver(pool)   # setup() 미호출 — DDL은 init.sql이 담당(아래)
  ```
  `autocommit=True`·`row_factory=dict_row`·`prepare_threshold=0`은 AsyncPostgresSaver/psycopg 풀 권장값
  (prepare_threshold=0은 풀러 환경의 prepared-statement 충돌 방지).

  **⚠️ DDL은 `deploy/postgres/init.sql`로만 관리한다 — `saver.setup()`(런타임 DDL)을 호출하지 않는다**(프로젝트
  스키마 관례: 수동 init.sql, create-all 없음). 런타임 DDL을 없애면 다중 인스턴스 동시 기동의 DDL 경쟁이
  **원천 제거**된다(ADR-0029 §A가 불필요해짐). 체크포인트 테이블은 init.sql에 선재해야 한다.

### 2. 그래프 라이프사이클 — import 시점 → lifespan

현재 `_graph`는 `domains/chat/service.py`에서 **import 시점** `build_chat_graph(..., checkpointer=build_checkpointer(settings.chat_checkpointer))`로
생성된다. postgres 풀은 **이벤트 루프 + 비동기 open**이 필요해 import 시점에 열 수 없다. 따라서:

- ⚠️ **import 시점은 설정과 무관하게 항상 InMemory로 빌드**한다(현재는 `build_checkpointer("postgres")`가
  import 시점에 호출돼 `NotImplementedError`로 **앱 기동이 실패** — 이 결함을 교정). 즉 import 경로에서
  postgres를 시도하지 않는다.
- **memory 모드(기본)**: import 시점 InMemory 그래프를 그대로 사용(변경 없음).
- **postgres 모드**: `main.py` lifespan **startup**에서 풀 open(테이블은 init.sql로 선재) 후 그래프를 **재빌드**해 모듈 핸들
  (`_graph`)을 **교체**하고, **shutdown**에서 풀을 닫는다. 서비스 `_run`은 매 호출 시 모듈 전역 `_graph`를 읽으므로
  교체가 그대로 반영된다(캡처 금지 — 전역 참조 유지).
- `domains/chat/service`에 `async def start_checkpointer()` / `async def stop_checkpointer()`를 노출하고
  `main.py` lifespan이 호출(엔진은 FastAPI 비의존 — 배선은 domain/main, ADR-0005). 풀 open 실패 시 기동을
  **명확히 실패**시킨다(조용한 memory 폴백 금지 — 운영에서 내구성 상실을 숨기지 않도록).

### 3. 스키마·운영

- **체크포인트 테이블 DDL은 `deploy/postgres/init.sql`로 관리**한다 — 런타임이 쓰는 **3개 테이블만**
  (`checkpoints`·`checkpoint_blobs`·`checkpoint_writes` + 인덱스). `checkpoint_migrations`와 버전 seed는 **두지 않는다**
  (그 테이블은 `setup()` 전용이고 런타임 aput/aget/alist/adelete는 참조하지 않음 — 패키지 소스로 확인).
- **개발 단계 정책 — migration 버전 관리 없음**: 스키마가 바뀌면(langgraph 업그레이드 등) 버전 추적·마이그레이션
  대신 **DB 볼륨을 재생성**한다(`task deploy-down ENV=<e>` → 재배포). 즉 "지우고 다시 생성". 운영 단계 진입 시
  정식 마이그레이션 전략은 별도 재검토.
- env(ADR-0018): `api.env.example`에 `CHAT_CHECKPOINTER=memory` 기본 문서화. 운영(stg/prd)에서 `postgres`로 토글.
- 동일 DB 컨테이너를 재사용(별도 인프라 불필요) — 좌표는 기존 `POSTGRES_*`.

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| **InMemory 유지** | 재시작·다중 인스턴스에서 HITL/되묻기/중단 재개 불가. 운영 전환 전 필수. |
| **sync `PostgresSaver`** | 그래프가 async(ADR-0026)라 `astream`과 짝이 안 맞음. AsyncPostgresSaver가 정합. |
| **앱 SQLAlchemy 엔진 공유** | langgraph saver는 autocommit·dict_row의 **전용 psycopg 연결**을 기대. 전용 풀이 단순·안전. |
| **별도 체크포인트 DB** | 운영 부담↑. 같은 `llmonl`에 search_path로 충분(격리는 테이블 네임스페이스). |
| **import 시점 풀 생성** | 이벤트 루프 부재 + 풀 수명 관리 불가. lifespan이 정석. |
| **`saver.setup()` 런타임 DDL** | 프로젝트 스키마 관례(수동 init.sql)에 위배 + 다중 인스턴스 DDL 경쟁. **init.sql로 관리**하고 setup() 미호출(버전 커플링은 감수). |

## Consequences (결과)

**긍정**
- 승인·되묻기·중단 대기가 **재시작·다중 인스턴스에서 내구적** — 재개가 안정적.
- ADR-0008 후속 완료. config 토글만으로 memory↔postgres 전환(테스트는 memory 유지 — 결정성·속도).
- 전용 풀이라 앱 DB 세션(ADR-0027 여부)과 **독립** — 이 ADR은 단독 진행 가능.

**부정 / 리스크**
- 그래프 생성이 import 시점 → lifespan으로 이동(postgres 모드) — 초기화 순서·실패 처리 필요(풀 open 실패 시 명확한 기동 에러).
- 체크포인트 테이블 증가 → 보존·정리 정책(오래된 thread 체크포인트 스윕) 후속 필요(ADR-0029).
- **버전 커플링(개발 단계 수용)**: DDL을 init.sql에 고정하므로 langgraph-checkpoint-postgres **업그레이드 시
  스키마가 바뀌면 init.sql 3-테이블 DDL을 재덤프**해야 한다. 개발 단계라 migration 없이 **볼륨 재생성**으로
  처리(데이터 보존 비요구). 운영 진입 시 정식 마이그레이션 전략 재검토.

**후속 작업**
- 체크포인트 보존/정리 + 승인 만료 스윕 — **ADR-0029**(다중 인스턴스 안전 스윕).
- 부하 테스트: 토큰 스트리밍 중 체크포인트 쓰기 지연 측정(ADR-0029 §C).
- 다중 인스턴스 기동 DDL 경쟁은 **init.sql 전환으로 해소**(런타임 setup() 제거).

## 검증 (구현 시)

1. **init.sql DDL**: 새 볼륨에서 `llmonl`에 checkpoint **3개 테이블** + 인덱스 생성 확인(migration 테이블·seed 없음).
2. `CHAT_CHECKPOINTER=postgres` 배포 → api가 `setup()` 없이 3개 테이블만으로 동작, healthy.
3. 되묻기/승인 중단 → **api 컨테이너 재시작** → `/clarify`·`/approvals` 재개가 정상 이어지는지(InMemory에선 실패했던 시나리오).

## 검증 (2026-11-21, stg / docker-desktop)

- 구현: `langgraph-checkpoint-postgres v3.2.1` 추가(uv.lock 재생성), `engine/graph/checkpointer.open_postgres_checkpointer`
  (AsyncPostgresSaver + psycopg AsyncConnectionPool, `autocommit`·`dict_row`·`prepare_threshold=0`·search_path=llmonl —
  **setup() 미호출**), `domains/chat/service.start_checkpointer/stop_checkpointer`(import 시점 InMemory → lifespan 교체),
  `main.py` lifespan 배선, `deploy/postgres/init.sql`에 checkpoint **3-테이블** DDL(migration 없음),
  `docker-compose.yml`·`api.env.example`에 `CHAT_CHECKPOINTER` 토글.
- `CHAT_CHECKPOINTER=postgres` 배포 → `llmonl`의 checkpoint 테이블(init.sql 관리)을 사용, api healthy.
- **재시작 내구성(핵심)**: 되묻기("번역해줘" → "어떤 언어로…" 중단)로 체크포인트 영속(`checkpoints` 3행) →
  **`docker restart` api** → `/clarify` 재개 성공 → 실모델 답변 "Have a nice day." 스트리밍. InMemory에선 소실돼
  실패하던 시나리오가 postgres로 **정상 동작**함을 확인.
- **migration 없는 3-테이블 런타임 검증**: 기존 `checkpoint_migrations`를 DROP 후 clarify ask→resume("Thank you.")
  정상 + 체크포인트 기록(6행) — 런타임이 `checkpoint_migrations`에 비의존함을 실증.
- init.sql 3-테이블 DDL은 scratch 스키마에서 생성 검증(테이블 3 + 인덱스, 오류 없음).
- memory 모드(기본)는 import 시점 InMemory 그대로라 무변경(start_checkpointer no-op).
