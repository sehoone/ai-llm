# ADR-0031: 구조화 로깅 + 요청 상관관계

- 상태: Proposed
- 날짜: 2026-11-23
- 결정자: sehoon
- 관련: [ADR-0007](0007-llm-observability-langfuse.md)(LLM 관측 — Langfuse), [ADR-0018](0018-env-config-layout.md)(env 단일 소스), [ADR-0005](0005-ai-engine-layer.md)(레이어 경계), [ADR-0027](0027-async-db-session.md)(async 요청 경계)

## Context (맥락)

로깅은 이미 **부분적으로** 돌아간다 — 하지만 설계된 적은 없다. 현재 사실:

- `main.py`에 `logging.basicConfig`로 루트 설정 1곳. 평문 포맷 `%(asctime)s %(levelname)s %(name)s: %(message)s`,
  레벨은 `settings.log_level`(기본 INFO).
- 도메인·엔진 전반이 `logging.getLogger(__name__)` 패턴을 지킨다(모듈별 네임스페이스 로거 — 좋음).
- 상당수 로그가 이미 **snake_case 이벤트 키** 스타일(`meeting_processing_start meeting_id=%s`,
  `workflow_execution_completed execution_id=%s`).
- 배포 스택에 **Loki + Promtail + Grafana** 존재(`deploy/`). Promtail이 docker stdout을 긁어 Loki로 push.
  현재 `pipeline_stages`는 평문에서 **정규식으로 `level`만** 추출 — 파일 주석에 `구조화 JSON 로깅 도입 시 json
  stage로 교체`라고 명시돼 있다.
- LLM 호출 관측은 Langfuse가 별도로 담당(ADR-0007) — 본 ADR 범위 아님(앱 로그 ↔ 트레이스 연결만 다룸).

이 상태의 **공백**(사실 확인):

1. **요청 상관관계 부재** — `request_id`가 없다. 동시 요청의 로그가 뒤섞여 한 요청의 흐름을 추적할 수 없다.
   비동기 스트리밍(ADR-0026)으로 요청 수명이 길고 겹쳐 더 심각하다.
2. **`extra={}`가 조용히 유실** — `markitdown.py`·일부 코드가 `logger.warning(..., extra={"path": ...})`를
   쓰지만, 현재 포맷 문자열이 `extra`를 출력하지 않아 그 필드는 **사실상 버려진다**.
3. **구조화(JSON) 로깅 없음** — Loki에 평문이 들어가 **필드 쿼리 불가**(level 라벨만). Promtail도 JSON 전환
   대기 중(위).
4. **앱 레벨 액세스 로그 없음** — uvicorn 기본 액세스 로그 외에 method·path·status·latency·user를 담는 요청
   로그가 없다. 느린 요청·4xx/5xx를 집계할 수단이 없다.
5. **메시지 컨벤션 혼재** — 이벤트키 스타일 ↔ 한국어 산문체(`seed 관리자 생성`, `DB 연결 실패`) 혼용. 팀 규칙 부재.

제약:
- **env 단일 소스(ADR-0018)** — 새 설정은 `api.env.example`(bare-metal localhost 기준) + docker는 compose
  `environment:` override.
- **레이어 경계(ADR-0005)** — `engine`은 `domains`·FastAPI를 import 금지. 로깅 설정·미들웨어는 **`core` 소유**,
  `engine`/`domains`는 `getLogger(__name__)`만 쓴다(설정에 무지).
- **의존성 최소** — 워크스페이스 관례상 불필요한 라이브러리 추가를 꺼린다.

## Decision (결정)

**stdlib `logging`만으로** (A) 포맷 전환 가능한 단일 설정 모듈 + (B) 요청 상관관계(contextvar+미들웨어) +
(C) 액세스 로그 미들웨어 + (D) 서드파티 로거 길들이기 + Promtail JSON stage를 도입한다. 라이브러리 추가 없음
(`structlog`/`python-json-logger` 기각 — §Alternatives).

### A. `core/logging.py` — 단일 로깅 설정 모듈

`main.py`의 `basicConfig`를 **`configure_logging()`**(core 소유)로 이전하고 `main.py` import 직후 1회 호출.
포맷을 env로 전환:

- `log_format=console`(로컬 dev 기본) — 사람이 읽는 평문(기존 포맷 유지 + `request_id` 접미).
- `log_format=json`(docker/prd 기본) — **한 줄 JSON**. Loki에서 필드 쿼리 가능.

`core/config.py`에 추가:
```python
log_format: str = "console"   # "console" | "json"
```

JSON은 **stdlib `logging.Formatter` 서브클래스**로 구현 — 의존성 0. 레코드 표준 필드 + `record.__dict__`의
`extra` 키를 병합해 직렬화(§B의 contextvar 필드도 자동 포함). 예:
```json
{"ts":"2026-11-23T10:00:00.123Z","level":"INFO","logger":"src.domains.meeting.service",
 "message":"meeting_processing_complete","request_id":"a1b2c3d4","user_id":42,"meeting_id":17}
```

### B. 요청 상관관계 — contextvar + 미들웨어

`core/logging.py`에 `ContextVar`(`request_id`, `user_id`)를 두고, **`logging.Filter`가 모든 레코드에 주입**한다.
어느 모듈이든 `logger.info("event", extra={...})`만 하면 `request_id`가 자동으로 붙는다 — 함수 시그니처로 id를
넘길 필요 없음(핵심 이점).

`core/middleware.py`에 `RequestContextMiddleware`(`main.py` `add_middleware`):
- 들어온 **`X-Request-ID` 헤더 재사용** 또는 신규 UUID 발급 → contextvar set.
- 응답 헤더에 **`X-Request-ID` echo**(nginx·프론트·클라이언트 추적).
- contextvar는 요청 단위 격리(ASGI). 비동기 스트리밍에서도 동일 컨텍스트 유지.

`user_id`는 **미들웨어가 JWT `sub`를 디코드해 best-effort 주입**한다(DB 조회·async 전환 없음 — §구현 현황의
회귀 노트 참고). 실제 인가는 핸들러 의존성(`get_current_user`)이 수행하며 **인증 로직은 변경 없음**.

### C. 액세스 로그 미들웨어

요청 1건당 1줄(완료/예외 모두). **본문은 로깅하지 않는다**(SSE 스트리밍·첨부·시크릿·로그 폭증 방지) — 디버깅용
메타데이터만:
```
http_request method=GET path=/api/v1/rag/keys query=type=chat status=200 duration_ms=20.6 client=203.0.113.9 user=42 req_bytes=0 resp_bytes=17
```
필드: `method`·`path`·`query`·`status`·`duration_ms`·`client`(X-Forwarded-For 우선)·`user`(user_id)·
`req_bytes`·`resp_bytes`. JSON 모드는 여기에 `user_agent`·`referer`까지 **구조화 필드**(`http_*`)로 추가(콘솔은
과밀 방지로 생략). 느린 요청·상태코드를 Grafana에서 집계. **uvicorn 기본 access 로그는 중복** →
`uvicorn.access` 레벨 WARNING으로 억제하고 이 미들웨어로 대체. 헬스체크(`/health`) 등 노이즈 경로는 DEBUG로 낮춤.

**`LOG_LEVEL=DEBUG` 상세** — 요약 라인 뒤에 `http_request_detail`(요청·응답 **본문**)을 추가. 헤더는 과밀해
넣지 않는다(필요한 user_agent·referer·client는 요약 라인/JSON에 이미 있음). 본문은 **안전 경계**를 둔다:
① **SSE**(text/event-stream)·비JSON(multipart·form·바이너리) 응답 본문은 미캡처(`(stream)`·`(non-json)` 사유
표기), ② **4KB 상한**(초과 요청 스킵·응답 절단), ③ JSON 본문의 **민감 필드**(`password`·`new_password`·
`access_token`·`secret`·`api_key` 등)는 `***` 마스킹. 요청 본문은 `receive`를 감싸 핸들러가 읽는 흐름 그대로
기록(별도 버퍼링 아님).

### D. 서드파티 로거 길들이기 + Promtail JSON stage

- `configure_logging()`에서 `httpx`·`httpcore`·`sqlalchemy.engine`·`apscheduler`·`python_multipart`를 기본
  WARNING(앱 `log_level=DEBUG`일 때만 수다). uvicorn 로거는 공존(`disable_existing_loggers=False` 유지).
- **Promtail `pipeline_stages`를 regex→`json` stage로 교체**(파일 주석대로) — `level`·`logger`·`request_id`를
  라벨/필드화. console 모드(dev)는 Promtail 미경유(bare-metal)라 무관.

### 설정 (ADR-0018 — `api.env.example` + config)
```
LOG_LEVEL=INFO           # 기존
LOG_FORMAT=console       # "console"(로컬 기본) | "json"
```
docker는 compose api `environment:`에 `LOG_FORMAT=json` override.

### 컨벤션 (팀 규칙 — CLAUDE.md "규칙"에 1줄 추가)
- **메시지 = snake_case 이벤트 키**(`meeting_processing_start`). 가변값은 **`extra={}`**(JSON 필드화) 또는
  `%s` lazy 포맷. **f-string 금지**(레벨 필터 전 평가 방지).
- **예외는 `logger.exception(...)`**(스택 포함). **비밀값 로깅 금지** — `db.py _masked_url()` 마스킹 패턴을 일반화.
- 레벨: DEBUG(개발 추적) / INFO(정상 수명주기) / WARNING(복구된 비정상) / ERROR(요청 실패) / CRITICAL(기동 불가).

### E. (선택) Langfuse 트레이스 연결
`engine/observability`가 trace id를 아는 지점에서 그 값을 contextvar/`extra`에 실으면, 로그에서 `trace_id`로
Langfuse 트레이스에 점프 가능. **도메인이 값 주입**(ADR-0005/0007 경계 — engine은 로깅 설정에 무지). 수요 시 후속.

## Alternatives considered (대안)

| 대안 | 기각/비고 |
|------|-----------|
| **`structlog` 도입** | 바인딩·프로세서 파이프라인이 강력하나 러닝커브·의존성 추가. 기존 `getLogger` 호출부를 전부 바꿔야 이점이 큼. 현재 규모엔 과함. |
| **`python-json-logger`** | stdlib 포매터를 JSON으로 바꿔주는 경량 패키지지만, 커스텀 Formatter 30줄로 동일 달성 → 의존성 불요. |
| **id를 함수 인자로 전파** | 명시적이나 모든 시그니처 오염 + 비동기/스트리밍에서 누락 위험. contextvar가 ASGI 요청 격리에 정확·무침습. |
| **uvicorn access 로그 유지** | 미들웨어 액세스 로그와 중복 + request_id·user_id 미포함. 앱 미들웨어로 대체가 정보량 우위. |
| **구조화 없이 평문 유지** | 변경 최소지만 Loki 필드 쿼리 불가·`extra` 유실 지속. JSON은 Promtail이 이미 대기 중이라 전환 비용 낮음. |
| **nginx/인프라에서만 액세스 로그** | 앱 내부 이벤트(user_id·도메인 컨텍스트)와 단절. 앱 로그가 요청 흐름에 더 밀착. |

## Consequences (결과)

**긍정**
- **요청 단위 추적** — `request_id`로 한 요청의 모든 로그를 Loki에서 묶어 조회(동시·스트리밍 요청에도 정확).
- **필드 쿼리 가능** — JSON + Promtail json stage로 `level`·`logger`·`request_id`·도메인 필드 집계/알림.
- **`extra` 유실 해소** — 기존 `extra={}` 코드가 비로소 의미를 가짐(코드 호출부 거의 불변).
- **의존성 0** — stdlib만. 기존 `getLogger(__name__)` 패턴·Loki 스택 그대로 재사용.
- **레이어 경계 유지** — 설정·미들웨어는 core, engine/domains는 로거만 사용(설정 무지).

**부정 / 리스크**
- JSON 로그는 로컬에서 사람이 읽기 불편 → `log_format=console` 기본(dev)로 회피.
- contextvar 누락 지점(미들웨어 밖 백그라운드 태스크·스케줄러 잡)은 `request_id`가 빈값 → 잡 진입 시 자체 id set
  권장(스케줄러·BackgroundTask).
- 컨벤션 통일은 점진 — 신규/수정 코드부터 적용, 기존 산문체 로그는 수요 시 리팩터(일괄 변경 안 함).

**후속 작업**
- Langfuse `trace_id` 연결(§E) — 로그↔트레이스 점프.
- Grafana 대시보드(요청률·에러율·p95 latency by path) + 알림.
- 슬로우 쿼리·체크포인트 쓰기 지연 구조적 로그(ADR-0029 §C와 연계).

## 전환 순서 (구현 시)
1. `core/logging.py`(`configure_logging` + console/json 포매터 + contextvar + Filter), `config.log_format` 추가,
   `main.py`가 basicConfig 대신 호출.
2. `RequestContextMiddleware`(request_id 발급·echo) + `get_current_user`에 user_id contextvar set.
3. 액세스 로그 미들웨어 + uvicorn access 비활성 + 서드파티 로거 레벨.
4. `api.env.example`·compose override(`LOG_FORMAT=json`) + Promtail json stage 교체.
5. CLAUDE.md "규칙"에 로깅 컨벤션 1줄.

## 검증 (구현 시)
- 동시 2요청의 로그가 각 `request_id`로 분리 조회됨. 응답 헤더에 `X-Request-ID` 존재.
- `log_format=json`에서 한 줄 유효 JSON + `extra` 필드 포함. `console`에선 사람이 읽는 평문.
- 액세스 로그 1줄/요청(status·duration_ms). `/health` 노이즈가 INFO에 안 뜸.
- Promtail json stage 적용 후 Loki에서 `{service="api"} | json | level="ERROR"` 쿼리 동작.

## 구현 현황 (2026-11-23)

**구현됨 (전환 순서 1~5 전부)**
- `core/logging.py` — `configure_logging()`(console/json 포매터 전환, 멱등), `ContextFilter`(request_id·user_id
  주입), `JsonFormatter`(extra 병합·exc/stack + `thread`·`thread_name`·`task_name` 포함), 서드파티 로거
  (httpx·httpcore·sqlalchemy.engine·apscheduler·python_multipart·**asyncio·litellm/LiteLLM**·uvicorn.access)
  WARNING 고정(DEBUG 플러딩 방지). `request_id_var`·`user_id_var` contextvar. 콘솔 프리픽스 `[request_id|threadName]`.
- `core/config.py` — `log_format: str = "console"` 추가.
- `core/middleware.py` — `RequestLoggingMiddleware`(**순수 ASGI**). X-Request-ID 재사용/발급 + 응답 헤더 echo +
  액세스 로그(4xx=WARNING·5xx=ERROR·`/health`=DEBUG) + 미처리 예외 로깅. `main.py`에 `add_middleware`.
  **user_id는 미들웨어가 JWT `sub`로 best-effort 주입**(DB 조회 없음·실패 시 "-"). API 키(sk-) 요청은 "-".
  액세스 로그 필드: `method·path·query·status·duration_ms·client(XFF 우선)·user·req_bytes·resp_bytes`,
  JSON 모드는 `user_agent·referer`까지 구조화(`http_*`). **`LOG_LEVEL=DEBUG`면 `http_request_detail`로 요청·응답
  본문을 추가**(헤더 제외, SSE·비JSON 본문 제외, 4KB 상한, password·token 등 민감 필드 `***` 마스킹).
- `main.py` — `basicConfig` → `configure_logging()`.
- `domains/auth/dependencies.py` — **변경 없음**(sync 유지). 당초 user_id contextvar 전파를 위해 `get_current_user`를
  async화했으나, 이 함수는 **동기 Session으로 블로킹 DB를 호출**해 async로 바꾸면 그 호출이 이벤트 루프를 막는다
  (느린 DB 연결 시 서버 전체 stall → 회귀). 되돌리고 user_id는 위 미들웨어 JWT 디코드로 해결.
- env/배포 — `local/api.env.example`에 `LOG_FORMAT` 주석(bare-metal=console), `docker-compose.yml` api
  `environment:`에 `LOG_FORMAT=json`, `promtail-config.yml`을 `match` 기반 json stage(api)+regex(그 외)로 교체
  (`level`만 라벨, request_id는 쿼리 시 `| json`).
- CLAUDE.md "규칙"에 로깅 컨벤션 1줄.

**미구현 (후속)**
- §E Langfuse `trace_id` 연결, Grafana 대시보드·알림. (ADR 본문 "후속 작업" 참고.)

> lint/test는 uv가 Claude 셸 PATH에 없어 미실행 — 사용자가 `uv run poe lint` / `poe test`로 확인 필요.
