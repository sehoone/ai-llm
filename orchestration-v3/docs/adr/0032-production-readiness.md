# ADR-0032: 상용 배포 준비 (production readiness)

- 상태: Proposed
- 날짜: 2026-11-28
- 결정자: sehoon
- 관련: [ADR-0003](0003-single-python-backend.md)(단일 백엔드), [ADR-0009](0009-self-id-password-auth.md)(자체 인증), [ADR-0017](0017-attachment-object-storage-minio.md)(MinIO), [ADR-0018](0018-env-config-layout.md)(env 단일 소스), [ADR-0019](0019-workflow-engine.md)(워크플로우 스케줄러), [ADR-0028](0028-langgraph-postgres-checkpointer.md)(Postgres 체크포인터), [ADR-0029](0029-chat-checkpointer-operations.md)(advisory lock 스윕), [ADR-0031](0031-structured-logging-and-request-context.md)(구조화 로깅·request_id)

## Context (맥락)

`apps/api`는 **기능적으로는 성숙**하다 — 수직 슬라이스·레이어 경계(ADR-0005)·구조화 로깅(ADR-0031)·HITL·관측 위임(ADR-0007)이 모두 잡혀 있다. 그러나 운영 토폴로지가 **"단일 인스턴스·단일 호스트" 전제**에 묶여 있어, 상용 배포 시 가장 먼저 깨진다. 코드·배포 구성을 점검해 확인한 공백(사실):

**A. 인스턴스-로컬 상태 — 수평 확장(레플리카 2+)을 막는다**
- `core/ratelimit.py` 인메모리 고정윈도우 — 주석에 "단일 프로세스 한정" 명시. 레플리카별 독립 카운터라 실효 한도가 N배.
- chat 체크포인터 기본 `memory`(`CHAT_CHECKPOINTER=memory`) — HITL 중단 세션이 인스턴스에 고립, 재시작 시 유실. postgres 모드(ADR-0028)는 구현됐으나 opt-in.
- `domains/workflow/scheduler.py` APScheduler가 **advisory lock 없이** 인프로세스 실행 → 레플리카마다 cron 중복 발화. (chat_maintenance는 ADR-0029에서 lock 보유, workflow는 없음.)
- `domains/meeting`이 `BackgroundTasks`로 STT·요약을 API 프로세스 안에서 실행 — 재시작 시 유실(`fail_stuck_meetings`로 FAILED 청소만), 레플리카 바인딩, 재시도 없음.

**B. 응답 계약 불일치**
- `main.py`에 전역 예외 핸들러가 없다. 미처리 예외(500)·검증 실패(422)·HTTPException이 FastAPI 기본 `{"detail": ...}`로 나가 **`ApiResponse[T]` 래퍼 계약(core/response.py)을 위반**한다. admin/portal axios 인터셉터는 `{success, data}` unwrap을 전제(ADR-0006)라 에러 응답이 제각각으로 보인다.

**C. 헬스 체크 미흡**
- `/health`가 단순 `{"status":"ok"}` 1종. **liveness ↔ readiness 구분이 없다.** 런타임 중 DB·스토리지 단절을 LB가 감지해 트래픽을 끊을 수단이 없다. (기동 시 `check_connection()` fail-fast는 있으나 런타임 프로브는 없음.)

**D. 보안·하드닝**
- nginx가 `:80`만 listen — **TLS 종단 없음**. JWT가 평문 HTTP로 흐른다.
- Dockerfile에 `USER` 없음 → **root 실행**. uvicorn에 `--proxy-headers`도 없어 프록시 뒤 scheme·client IP 신뢰 경계가 불명확.
- `TrustedHostMiddleware` 없음 → Host 헤더 스푸핑 무방비.
- 시크릿(JWT·DB·MinIO·LLM 키)이 `api.env` 평문. refresh/폐기 없는 24h JWT.

**E. 관측·HA (중기)**
- `prometheus.yml`이 `api:8000/metrics`를 스크레이프하도록 설정돼 있으나 **엔드포인트가 없어 계속 404**.
- Postgres·MinIO·ClickHouse·Redis가 **단일 컨테이너 SPOF**. DB 백업/복구 런북 전무. compose 리소스 limit 없음. Alertmanager 규칙 없음.

**제약 (결정에 영향):**
- **Redis를 앱 의존성으로 추가하지 않는다** — compose의 `redis`는 Langfuse 전용. 앱의 외부 상태는 **Postgres + MinIO** 둘로 한정(이미 advisory lock·pgvector·체크포인터를 Postgres로 쓰므로 일관적).
- **스키마 마이그레이션 도구 미도입** — DDL은 수동 실행(`init.sql` + `deploy/postgres/migrations/*.sql`, 멱등 `IF NOT EXISTS`). Alembic 등 러너 도입하지 않음.
- **env 단일 소스(ADR-0018)** — 새 설정은 `api.env.example`(bare-metal) + docker는 compose override.
- **레이어 경계(ADR-0005)** — 설정·미들웨어·에러 핸들러는 `core` 소유. engine은 FastAPI 무지.

## Decision (결정)

상용 준비를 **3 Phase**로 나눈다. **Phase 1(상용 게이트)**을 본 ADR에서 구현하고, Phase 2·3은 결정·근거만 남겨 후속 작업으로 둔다.

### Phase 1 — 상용 게이트 (본 ADR에서 구현)

**1. 전역 예외 핸들러 — 응답 계약 정규화** (`core/errors.py`)
세 부류를 `ApiResponse(success=False)` 한 포맷으로 묶는다. 바디에 `request_id`(ADR-0031 contextvar)를 실어 로그↔응답을 상관.
- `HTTPException`(starlette 베이스로 등록 — fastapi 서브클래스 + 라우팅 404/405 포괄) → status 유지 + detail→message.
- `RequestValidationError` → 422 + 첫 오류를 message로, 전체는 `data.errors`.
- 그 외 `Exception` → 500 + 고정 메시지(내부 상세 비노출) + `logger.exception`.
`main.py`가 `register_exception_handlers(app)` 1회 호출. `ApiResponse.fail()` 클래스메서드 추가.

**2. 헬스 분리 — liveness ↔ readiness** (`main.py` + `core/db.ping` + `core/storage.check_storage`)
- `/health`·`/health/live`: 프로세스 생존만(의존성 미조회) — k8s/compose 재시작 판단. `/health`는 **하위호환 별칭**(nginx `location = /health`·docker healthcheck 유지).
- `/health/ready`: **DB(hard)** + **스토리지(soft)** 확인. DB 실패 시 **503**(LB가 트래픽 차단), 스토리지는 다운돼도 텍스트 챗이 동작하므로 readiness를 깨지 않고 `checks`로 상태만 보고. `db.ping()`은 성공 로깅 없는 조용한 점검(프로브 노이즈 방지).

**3. 보안 하드닝**
- `TrustedHostMiddleware`(`config.allowed_hosts`, 콤마 구분; `"*"`면 미적용) — Host 스푸핑 차단. stg/prd는 실제 도메인으로 좁힘.
- Dockerfile **non-root**(`appuser` uid 10001, `/app`·`/data` 소유권) + uvicorn `--proxy-headers --forwarded-allow-ips "*"`.
- nginx `/api/`에 `X-Forwarded-Proto $scheme` 추가 — 앞단 TLS 종단 시 api가 https 인식.
- **TLS는 배포 요구사항으로 명문화**(인증서는 환경별이라 레포에 하드코딩 안 함) — 앞단 LB/Ingress 또는 nginx TLS 블록에서 종단. `X-Forwarded-Proto`·`--proxy-headers`로 앱 준비 완료.

**4. 상용 기본값**
- stg/prd `compose.env.example`·`api.env.example`에 `CHAT_CHECKPOINTER=postgres`(ADR-0028 내구화). 체크포인트 테이블은 `llmonl`에 **수동 DDL** 선생성.
- stg/prd `api.env.example`에 `ALLOWED_HOSTS=<도메인>`. 시크릿은 `deploy.py`가 REPLACE_ME를 거부(기존) — 평문 저장은 Phase 2에서 secrets manager로.

### Phase 2 — 스케일 안전 (후속, Redis-free)

| 항목 | 설계 (저장소) |
|------|--------------|
| 레이트리밋 | `core/ratelimit.py` 인메모리 제거 → **nginx `limit_req_zone`**(단일 진입점이라 레플리카 무관 전역 일관). 유저 단위 한도가 필요하면 Postgres UPSERT 카운터 병행. |
| workflow 스케줄러 | 발화 전 **`pg_try_advisory_lock`**(chat_maintenance 패턴 재사용)으로 리더만 실행 → cron 중복 제거. 또는 단일 scheduler 전용 디플로이로 분리. |
| 장기 작업 큐 | meeting STT·요약 등을 `BackgroundTasks` → **Postgres `SELECT … FOR UPDATE SKIP LOCKED` 큐**(procrastinate/pgqueuer 또는 경량 커스텀) + 별도 `worker` 프로세스(동일 이미지, CMD만 다름). 재시작 내구·재시도·레플리카 분산. `fail_stuck_meetings`는 "visibility timeout 재큐잉"으로 승격. |
| `/metrics` | `prometheus-fastapi-instrumentator` 또는 `prometheus_client`로 노출(요청 수·지연·상태코드) — prometheus 스크레이프 이미 설정됨. Alertmanager 에러율·지연·디스크 규칙. |
| JWT 폐기 | 단기 access + refresh(`llmonl.refresh_token` 신설) 또는 `jti` 블랙리스트(`llmonl.revoked_token`, 만료까지 보관·maintenance 스윕 재사용). |

### Phase 3 — HA (후속)

- 관리형 Postgres(+PITR 백업)·관리형/S3 객체스토리지로 외부화 — SPOF 제거. 최소한 **DB 백업/복구 런북** 작성.
- compose 리소스 limit(cpu/mem). 무중단 배포·롤백·오토스케일 필요 시 **k8s/Ingress 이행**(CLAUDE.md의 dormant CI도 함께 정리).

### 수동 DDL 운영 수칙 (마이그레이션 도구 미도입 전제)
- DDL은 **멱등·순방향**(`CREATE/ADD … IF NOT EXISTS`). 배포 재실행 안전.
- `migrations/NNNN_*.sql` 번호순 유지 + 상용 적용분 추적(런북 또는 `llmonl.schema_history` 수동 기록).
- 앱은 `create_all()` 호출 안 함 — 스키마는 DDL이 소유, 앱은 기동 시 `check_connection`만. **배포 순서 = ①DDL 수동 실행 → ②api 배포**를 런북에 명시.
- 파괴적 DDL(`DROP`·타입변경)은 롤백 SQL 자동 생성 없음 → 배포 전 백업 확인을 체크리스트에.

## Alternatives considered (대안)

| 대안 | 기각/비고 |
|------|-----------|
| **Redis로 레이트리밋·큐·세션** | 고throughput엔 유리하나 앱에 새 상태저장소 의존 추가. 이 워크로드(사내 LLM 오케스트레이션) 규모엔 nginx+Postgres로 충분 — 운영 표면 최소화(제약). |
| **Alembic 등 마이그레이션 도구** | 버전·롤백 자동화가 이점이나 팀이 수동 DDL 운영을 선택(제약). 멱등 SQL + 번호순 파일 + 런북으로 대체. |
| **readiness에서 스토리지도 hard** | MinIO 다운 시 텍스트 챗까지 차단 — 과도. soft 보고로 부분 가용성 유지(첨부·회의만 영향). |
| **HTTPException 핸들러를 fastapi.HTTPException에 등록** | starlette 원형(라우팅 404/405)을 놓쳐 500으로 오분류. starlette 베이스 등록이 MRO로 둘 다 포괄. |
| **500 응답에 예외 메시지 노출** | 디버깅 편하나 내부 구조 유출. `request_id`로 로그 추적 — 메시지는 고정. |
| **앱 내 uvicorn `--workers`로 멀티프로세스** | 인스턴스-로컬 상태(ratelimit·스케줄러·BackgroundTask)가 워커 간에도 깨짐 → Phase 2 선행 필요. 지금은 레플리카/워커 전에 상태 외부화가 먼저. |
| **TLS를 nginx.conf에 하드코딩** | 인증서가 환경별·비밀이라 레포 커밋 부적합. `X-Forwarded-Proto`·`--proxy-headers`로 앱만 준비하고 종단은 배포 인프라에 위임. |

## Consequences (결과)

**긍정**
- 에러 응답이 `ApiResponse` 계약으로 통일 — 프론트 unwrap 일관, `request_id`로 로그↔응답 상관.
- readiness로 DB/스토리지 단절 시 LB가 트래픽을 끊어 **부분 장애가 전면 5xx로 번지지 않음**.
- non-root·TrustedHost·proxy-headers로 기본 공격면 축소. TLS 수용 준비 완료.
- 상용 기본값(postgres 체크포인터)으로 재시작·다중 인스턴스에서 HITL 세션 내구.
- Phase 2·3이 **Redis 없이 Postgres+nginx**로 설계돼 운영 표면이 작고 기존 패턴과 일관.

**부정 / 리스크**
- Phase 1만으로는 **아직 수평 확장 불가** — ratelimit·workflow 스케줄러·meeting 큐(Phase 2)가 레플리카 안전의 전제. 당분간 **단일 레플리카** 운영.
- readiness가 매 프로브마다 DB·MinIO를 때리므로 프로브 간격을 과도히 짧게 두면 부하 — 간격 튜닝 필요(예: 10~30s).
- TrustedHost 설정을 `*`로 두면 무효 — stg/prd에서 실제 도메인 지정이 운영 책임.
- 수동 DDL은 휴먼 에러 여지 — 배포 순서·백업 체크리스트 준수에 의존.

**후속 작업**
- Phase 2: nginx `limit_req`, workflow advisory lock, Postgres `SKIP LOCKED` 큐 + worker, `/metrics`, JWT 폐기.
- Phase 3: DB 백업/PITR·외부화, 리소스 limit, (필요 시) k8s 이행, Alertmanager.

## 전환 순서 (구현 시)
1. `ApiResponse.fail` + `core/errors.py`(3 핸들러) + `main.py` 등록.
2. `core/db.ping` + `core/storage.check_storage`/`health()` + `/health/live`·`/health/ready`(+ `/health` 별칭).
3. `config.allowed_hosts` + `TrustedHostMiddleware` + Dockerfile non-root·`--proxy-headers` + nginx `X-Forwarded-Proto`.
4. stg/prd env(`CHAT_CHECKPOINTER=postgres`·`ALLOWED_HOSTS`) + local env 주석.

## 검증 (구현 시)
- 존재하지 않는 경로/검증 실패/강제 예외가 모두 `{success:false, message, request_id}` 형태 + 적절한 status(404·422·500).
- `/health`·`/health/live` 200, `/health/ready`가 DB 연결 시 200·checks ok / DB 중단 시 503.
- `ALLOWED_HOSTS` 좁힌 환경에서 허용 외 Host 헤더 요청이 400. 허용 Host는 정상.
- 컨테이너가 비루트(`whoami`=appuser)로 기동, nginx 뒤 client IP·scheme 복원(액세스 로그 client·X-Forwarded-Proto).
- `pytest tests/test_health.py` 통과(live·ready checks 키).

## 구현 현황 (2026-11-28)

**구현됨 (Phase 1 — 전환 순서 1~4 전부)**
- `core/response.py` — `ApiResponse.fail(message, data)` 추가.
- `core/errors.py`(신규) — `register_exception_handlers(app)`: HTTPException(starlette 베이스)·RequestValidationError(422, `data.errors`)·Exception(500, `logger.exception`, 상세 비노출). 바디에 `request_id` 포함.
- `main.py` — `register_exception_handlers(app)` 호출. `TrustedHostMiddleware`(allowed_hosts ≠ `["*"]`일 때). `/health`·`/health/live`(얕음) + `/health/ready`(DB hard→503, 스토리지 soft→`checks` 보고).
- `core/db.py` — `ping()`(조용한 readiness 점검). `core/storage.py` — `FileStorage.health()`(local=쓰기 가능, minio=`bucket_exists`) + `check_storage()`.
- `core/config.py` — `allowed_hosts: str = "*"` + `allowed_hosts_list` 프로퍼티.
- `apps/api/Dockerfile` — non-root `appuser`(uid 10001) + `--proxy-headers --forwarded-allow-ips "*"`.
- `deploy/nginx/nginx.conf` — `/api/`에 `X-Forwarded-Proto $scheme`.
- env — stg/prd `compose.env.example`·`api.env.example`에 `CHAT_CHECKPOINTER=postgres`, stg/prd `api.env.example`에 `ALLOWED_HOSTS`, local `api.env.example`에 `ALLOWED_HOSTS` 주석.
- `tests/test_health.py` — `/health/live`·`/health/ready`(checks 키) 테스트 추가.
- `tests/test_error_handlers.py`(신규) — 404·422·500 정규화(success=false·message·request_id, 내부 상세 비노출) 검증.

**검증 (2026-11-28 실행)**
- `uv run ruff check`(변경 파일) + `uv run lint-imports`(레이어 경계 2 kept/0 broken) 통과.
- `uv run pytest` — 전체 35건 통과(신규 health 3 + error-handler 3 포함, 회귀 없음).
- Dockerfile non-root 변경은 이미지 빌드 미실행(로직 검토만) — 실배포 전 `task deploy ENV=stg`로 빌드·기동 확인 권장.

**미구현 (후속 — Phase 2·3)**
- 본문 §Phase 2·3 전부(레이트리밋 nginx 이전, workflow advisory lock, Postgres SKIP LOCKED 큐+worker, `/metrics`+Alertmanager, JWT 폐기, DB 백업/외부화, 리소스 limit).
- TLS 실제 종단 구성(배포 인프라 — 본 ADR은 앱/프록시 수용 준비까지).

> lint/test는 uv가 Claude 셸 PATH에 없어 미실행 — 사용자가 `uv run poe lint` / `uv run poe test`로 확인 필요. (`py_compile` 구문 검사만 수행.)
