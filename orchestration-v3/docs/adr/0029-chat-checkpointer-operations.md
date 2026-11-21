# ADR-0029: chat 체크포인터·승인 운영 (정리·기동 경쟁·관측)

- 상태: Proposed
- 날짜: 2026-11-21
- 결정자: sehoon
- 관련: [ADR-0028](0028-langgraph-postgres-checkpointer.md)(Postgres 체크포인터), [ADR-0008](0008-chat-human-approval.md)(승인 만료 스윕 후속), [ADR-0019](0019-workflow-engine.md)(APScheduler 패턴), [ADR-0018](0018-env-config-layout.md)(env)

## Context (맥락)

ADR-0028로 Postgres 체크포인터가 들어오면서 **운영 숙제 3가지**가 생겼다(0028 §후속):

1. ~~**다중 인스턴스 기동 경쟁** — 각자 `saver.setup()`(DDL)을 돌려 동시 DDL 충돌 위험.~~
   → **해소됨**: ADR-0028을 "DDL은 init.sql로만 관리(setup() 미호출)"로 개정하면서 **런타임 DDL이 사라져
   경쟁이 원천 제거**됐다. 본 ADR에서 별도 가드(advisory lock on setup)는 **불필요**(§A 참고).
2. **체크포인트 무한 증가** — 모든 thread·슈퍼스텝이 `checkpoints`·`checkpoint_blobs`·`checkpoint_writes`에
   행을 쌓는다. 정리 정책이 없다. 또한 현재 `ChatService.delete_session`은 체크포인트를 안 지워 **고아
   thread**가 남는다(세션·메시지·승인·첨부만 정리). ADR-0008의 미결 **승인(`chat_approval` PENDING) 만료
   스윕**도 아직 없다.
3. **부하·지연 미측정** — 토큰 스트리밍 중 체크포인트 쓰기가 토큰 지연에 주는 영향을 모른다.

제약(사실 확인):
- 체크포인트 테이블에 **timestamp 컬럼이 없다**(`thread_id·checkpoint_ns·checkpoint_id(uuid)·…`). → TTL은
  체크포인트 자체 시각이 아니라 **`chat_session` 생명주기**(thread_id=`"{session.id}:{thread_rev}"`)에 연동한다.
- AsyncPostgresSaver는 **`adelete_thread(thread_id)`** 공식 API 제공(3개 테이블 일괄 삭제).
- APScheduler(`AsyncIOScheduler`)가 이미 워크플로우(ADR-0019)에서 쓰인다 — lazy import·미설치 no-op 패턴.
- 레이어(ADR-0005): 정리·스케줄은 **인프라 트리거라 domain 소유**(engine 금지, 0019와 동일 논리).

## Decision (결정)

두 숙제를 **(B) 유지보수 스윕(정리+승인만료) · (C) 관측·부하 측정**으로 해결한다. 스윕은 **Postgres
advisory lock**으로 다중 인스턴스 안전(중복 방지)을 보장한다. (A)는 ADR-0028 개정으로 불필요해졌다.

### A. 기동 경쟁 가드 — 불필요 (ADR-0028 개정으로 해소)

당초 `saver.setup()` 런타임 DDL의 다중 인스턴스 경쟁을 advisory lock으로 직렬화하려 했으나, **ADR-0028을
"DDL은 `deploy/postgres/init.sql`로만 관리, `setup()` 미호출"로 개정**하면서 런타임 DDL 자체가 사라졌다.
init.sql은 DB 볼륨 최초 1회만 실행(멱등 CREATE IF NOT EXISTS)되므로 **인스턴스 기동과 무관** → 별도 가드 불요.
(advisory lock은 §B 스윕 중복 방지에만 사용.)

### B. 유지보수 스윕 (정리 + 승인 만료)

도메인 소유 **단일 유지보수 잡**이 둘을 함께 처리한다(ADR-0008 승인 스윕 + ADR-0028 정리 통합):

**① 체크포인트 보존 — `chat_session` 연동**
- **세션 삭제 시 즉시 정리**: `ChatService.delete_session`이 `for rev in 0..thread_rev: await saver.adelete_thread(f"{id}:{rev}")`
  를 추가 호출(고아 생성 차단). memory 모드면 no-op. (delete 경로를 async로 — 소규모 변경.)
- **주기 스윕**: 아래 후보 thread를 `adelete_thread`로 제거.
  - **고아**: `checkpoints`의 `thread_id` prefix(session id)가 `chat_session`에 **없는** 것(과거 삭제 잔재) → 즉시 제거.
  - **비활성 만료**: `chat_session.updated_at < now - retention_days`인 세션의 thread(기본 30일). 활성 대화는
    보존(장기 대화가 재개 능력을 잃지 않도록 — 시각 TTL이 아닌 **세션 비활성** 기준).
  - 후보 집합은 SQL 조인(`checkpoints` DISTINCT thread_id ↔ `chat_session`)으로 뽑고, 공식 `adelete_thread`로
    삭제(3개 테이블 + 향후 스키마 변화 대응).

**② 승인 만료 (ADR-0008 후속)**: `chat_approval` 중 `status=PENDING AND expires_at < now`를 `EXPIRED`로 마킹
  (이미 `chat_approval_ttl_seconds`로 만료시각 기록 중 — 스윕만 없었음). 재개 fail-safe와 정합.

**실행 메커니즘**:
- APScheduler `AsyncIOScheduler`(ADR-0019 패턴 재사용)에 **간격/cron 잡** 1개 등록(`main.py` lifespan). lazy
  import·미설치 no-op. 도메인에 `domains/chat/maintenance.py`(또는 service 함수) `async def sweep()`.
- **다중 인스턴스 안전**: `sweep()` 진입 시 `pg_try_advisory_lock(SWEEP_LOCK)` — 획득 실패(다른 인스턴스가 수행
  중)면 즉시 반환. 중복 스윕 방지.
- 새 Session을 열어 후보 조회, saver는 모듈 전역(활성 체크포인터)을 사용. memory 모드면 체크포인트 정리는
  skip(승인 만료만 수행).

### C. 관측·부하 측정

- **메트릭(기존 스택 재사용)**: Prometheus+Grafana(스택 존재)로 Postgres·psycopg **풀 포화·쿼리 지연**을 관찰.
  AsyncConnectionPool 통계(대기·사용 커넥션)를 주기 로깅 또는 Prometheus 게이지로 노출(경량).
- **부하 테스트 절차(tools/)**: 동시 N 스트리밍 세션으로 **memory vs postgres** 체크포인터의 첫 토큰·토큰 간
  지연을 비교 측정하는 스크립트. 체크포인트 쓰기가 토큰 지연에 유의미하면(임계 초과) 후속으로 **쓰기 비동기
  배치/핫패스 분리**를 검토(지금은 측정 가드만 — 섣부른 최적화 금지).
- 느린 체크포인트 쓰기 임계 초과 시 구조적 로그(선택).

### 설정 (ADR-0018 — `api.env.example` + config)
```
CHAT_MAINTENANCE_ENABLED=true            # 유지보수 스윕 on/off
CHAT_MAINTENANCE_CRON=0 3 * * *          # 기본 매일 03:00 UTC
CHAT_CHECKPOINT_RETENTION_DAYS=30        # 세션 비활성 보존 기간(일)
```
`CHAT_CHECKPOINTER=memory`면 체크포인트 정리는 자동 skip(승인 만료 스윕은 유지).

## Alternatives considered (대안)

| 대안 | 기각/비고 |
|------|-----------|
| **시각 TTL로 모든 체크포인트 일괄 삭제** | 체크포인트에 timestamp 없음 + 활성 장기 대화의 재개 능력 상실. `chat_session` 연동이 정확. |
| **(기동 경쟁 가드)** | 불요 — ADR-0028을 init.sql DDL(setup() 미호출)로 개정해 런타임 DDL·경쟁이 소멸(§A). |
| **직접 SQL 대량 DELETE** | 더 빠르나 3개 테이블·스키마 변화에 취약. 일 1회 규모엔 공식 `adelete_thread`가 안전·미래지향. |
| **인스턴스마다 스윕(락 없음)** | 중복 작업·부하. `pg_try_advisory_lock`으로 1개만 수행. |
| **외부 cron + 관리자 엔드포인트** | 인프라 결합 적으나 자동화 약함. 이미 APScheduler 보유 → 재사용이 단순. |
| **승인 스윕과 분리된 별도 잡** | 둘 다 chat 유지보수·동일 주기 → 단일 잡으로 묶어 단순화(advisory lock 1회). |

## Consequences (결과)

**긍정**
- **스윕 단일화**(advisory lock 중복 방지). 기동 경쟁은 ADR-0028 init.sql 전환으로 이미 해소.
- 체크포인트 **무한 증가 차단** + 세션 삭제 **고아 회수**. ADR-0008 **승인 만료 스윕 완성**.
- 관측·부하 가드로 체크포인트 비용을 **데이터로** 판단(필요 시만 추가 최적화).
- memory 모드·단일 인스턴스엔 영향 최소(정리 skip, 승인 스윕만).

**부정 / 리스크**
- `delete_session` 즉시 정리를 위해 해당 경로 async화(소규모). 스윕은 활성 대화를 지우지 않도록 **비활성 기준**
  신중 설정(기본 30일) — 너무 짧으면 재개 가능 창을 줄임.
- advisory lock 키 충돌 방지 위해 전역 상수 관리 필요.
- 보존 삭제는 비가역 — retention_days·cron은 운영에서 신중히.

**후속 작업**
- 부하 측정 결과에 따라 체크포인트 쓰기 핫패스 최적화(비동기 배치) 여부 결정.
- 보존 정책을 프로젝트/중요 대화별로 차등(핀 고정 대화 보존) — 수요 시.

## 전환 순서 (구현 시)
1. 승인 만료 스윕(`chat_approval`) + 유지보수 잡 골격(APScheduler + `pg_try_advisory_lock`) — ADR-0008 숙제 해소.
2. 체크포인트 보존(세션 삭제 즉시 정리 + 주기 스윕의 고아·비활성 제거).
3. 관측(풀 통계) + 부하 테스트 스크립트(memory vs postgres) → 최적화 요부 판단.
> 기동 경쟁 가드(구 §A)는 ADR-0028 init.sql 전환으로 **불요** — 구현 항목 아님.

## 검증 (구현 시)
- 다중 인스턴스 동시 기동(2+ api)에서 오류 없이 모두 healthy(런타임 DDL 없음).
- 세션 삭제 → 해당 thread 체크포인트 사라짐. 오래된/고아 thread가 스윕 후 제거.
- 만료된 PENDING 승인이 `EXPIRED`로 마킹·재개 fail-safe 동작.
- 부하 스크립트로 memory 대비 postgres 토큰 지연 증가분 수치화.
