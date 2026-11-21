# ADR-0027: 비동기 DB 세션 (AsyncSession / psycopg async)

- 상태: Proposed (권고: 단계적·조건부 — 아래 §결정 참고)
- 날짜: 2026-11-21
- 결정자: sehoon
- 관련: [ADR-0026](0026-chat-async-streaming.md)(chat async 스트리밍 — 이 ADR의 계기), [ADR-0005](0005-ai-engine-layer.md)(경계), [ADR-0018](0018-env-config-layout.md)(env)

## Context (맥락)

ADR-0026으로 chat 스트리밍 경로가 async가 됐다. 그 과정에서 느린 블로킹 사이드콜(RAG·추출·메모리·제목)은
`run_in_threadpool`로 격리했지만, 스트리밍 루프 **내부의 소형 DB 쓰기**(assistant/tool 메시지 영속, 승인 저장,
아티팩트 upsert)는 **인라인 sync**로 남겨뒀다 — 턴 경계라 빈도가 낮고 수 ms라 실용상 허용. 또한
`get_current_user`·대부분의 CRUD 엔드포인트는 여전히 sync `Session`(스레드풀 실행)이다.

전면 `AsyncSession` 전환의 잠재 이득: (a) 이벤트 루프 블로킹 완전 제거, (b) 고동시성에서 스레드풀 포화 회피.
비용: `get_session` 사용처 ~20곳, repo ~26개, 그 위 서비스·엔드포인트·인증 의존성까지 **광범위 파급**.

드라이버는 **psycopg3**(`postgresql+psycopg://`)라 async를 네이티브 지원한다 — asyncpg 추가 불필요.

## Decision (결정)

**전면 즉시 전환은 하지 않는다.** 현재 규모에서 ADR-0026의 `run_in_threadpool` 브리지로 이벤트 루프는
충분히 보호된다. AsyncSession은 **고동시성 프로파일링에서 스레드풀 포화가 실제 병목으로 확인될 때** 또는
독립적 동기(예: 전면 async 표준화)가 생길 때 **단계적으로** 도입한다. 본 ADR은 그 때의 설계를 확정해 둔다.

### 설계 (도입 시)

**인프라 (`core/db.py`)** — sync와 **공존**하며 점진 이전:
```
async_engine = create_async_engine(
    settings.database_url,  # postgresql+psycopg:// → psycopg3 async
    pool_pre_ping=True, pool_recycle=1800,
    connect_args={"options": "-csearch_path=llmonl,public"},
)
async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSession(async_engine) as s:  # sqlmodel.ext.asyncio.AsyncSession
        yield s
```
sync `engine`/`get_session`은 **유지**(미이전 도메인·배경 작업·saver 무관 코드). 두 세션은 **트랜잭션을 공유하지 않으므로** 한 요청 경로에서 혼용 금지(도메인 단위로 완전 이전).

**이전 패턴 (repo → service → api, 도메인 단위)**:
- repo: `self.session.exec(...)` → `await self.session.exec(...)`, `commit/refresh`도 `await`. 메서드 `async def`.
- service: repo 호출부 `await`, 메서드 `async def`.
- api: 엔드포인트 `async def` + `Depends(get_async_session)`.
- `get_current_user`(인증 의존성)는 모든 보호 엔드포인트에 걸리므로 **가장 먼저 async 버전**(`get_async_session` 사용) 필요. 혼용 과도기에는 sync/async 두 벌을 두거나, 인증만 먼저 async로 전환하고 sync 세션을 별도 조회로 유지.

### 단계 (권장 순서)
1. **Phase A — 인프라**: async 엔진·`get_async_session`·async `get_current_user` 추가(sync와 공존, 기존 불변).
2. **Phase B — chat 핫패스**: `ChatRepository`·`ArtifactRepository`를 async로 이전 → `_run` 인라인 DB 쓰기의 이벤트 루프 블로킹 제거(ADR-0026 §5 인라인 잔여 해소). chat 서비스·엔드포인트 async.
3. **Phase C — 나머지 도메인**: 부하·필요에 따라 도메인 단위로 순차 이전. 완료 시 sync `Session` 제거.

> **1차 권고: Phase A/B만 조건부 진행, Phase C는 보류.** 측정 없는 전면 전환은 비용 대비 이득이 불명확하다.

## Alternatives considered (대안)

| 대안 | 평가 |
|------|-----------|
| **현상 유지(run_in_threadpool 브리지)** | **1차 권장.** 루프 블로킹은 이미 완화. 인라인 소형 DB 쓰기는 턴 경계·수 ms로 실용상 무해. |
| **전면 즉시 AsyncSession** | 26 repo + 20 의존성 파급 — 대규모 churn·회귀 위험. 측정된 병목 없이는 과투자. |
| **asyncpg 드라이버 채택** | 불필요. psycopg3가 이미 async 지원 — 드라이버 이원화 회피(ADR-0015 mem0가 psycopg_pool 사용). |
| **동기 유지 + 스레드풀 상한만 확대** | 임시방편. 포화 시 지연 증가. 근본은 async이나 그건 Phase B로. |

## Consequences (결과)

**긍정(도입 시)**
- chat 스트리밍 루프의 인라인 DB 쓰기까지 **완전 비차단** → 고동시성 지연·꼬리 레이턴시 개선.
- psycopg3 재사용 — 드라이버 단일.

**부정 / 리스크**
- **광범위 파급**: repo·service·endpoint·인증 의존성 전반. 단계·도메인 단위로 쪼개지 않으면 회귀 위험 큼.
- sync·async 세션은 **트랜잭션 비공유** → 과도기 혼용 금지(도메인 경계로 분리).
- SQLModel async(`sqlmodel.ext.asyncio`) 사용 패턴 숙지 필요(`exec` await, lazy-load 주의).

**후속 작업**
- 동시성 프로파일링(스레드풀 포화·DB 대기 측정)으로 **도입 판단 근거** 확보.
- 도입 결정 시 Phase A→B 먼저, 측정 재평가 후 Phase C.
