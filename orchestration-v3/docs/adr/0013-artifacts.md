# ADR-0013: 아티팩트 (스트림 파서 + artifact 도메인 + 버저닝)

- 상태: Accepted
- 날짜: 2026-11-07
- 결정자: sehoon
- 관련: [ADR-0011](0011-chat-streaming-contract.md)(스트림 계약 — `artifact_*` 예약), [ADR-0005](0005-ai-engine-layer.md)(경계), [ADR-0008](0008-chat-human-approval.md)(그래프)
- 참조: V2 `chatbot/services/artifact_stream_parser.py`, `artifact/{api,models,schemas,services}`, `chatbot/api/chatbot_api.py`(chat_stream 아티팩트 처리), web `api/artifacts.ts`·`stores/artifact-store`·`features/artifacts`
- 로드맵: [v2-chat-migration-roadmap](../v2-chat-migration-roadmap.md) Phase 3

## Context (맥락)

LLM이 코드·문서·다이어그램·웹페이지 등 **자립적 산출물**을 낼 때, chat 버블에 코드펜스로 쏟지 않고
**아티팩트**(별도 캔버스 + 버전관리 + 공개 링크)로 다룬다. V2는 LLM이 토큰 스트림 안에 인라인
태그를 넣고(`<artifact identifier= type= title=>…</artifact>`), 서버가 스트림 파서로 **chat 본문과
아티팩트 본문을 분리**해 SSE로 내보내며, 아티팩트는 버전 테이블에 영속한다.

전제:
- **web은 이미 완비**: `artifactService`(list·get·versions·publish·data·public), `artifact-store`,
  `artifact-panel`, 라이브러리 화면, 스트림 이벤트 타입. V3에서 끊긴 건 **chat 스트림 배선과 백엔드**.
- ADR-0011이 `artifact_start|delta|end` 이벤트를 이미 예약. V3 chat SSE는 event-프레이밍이라 그대로 추가.
- 데이터모델 차이: V2 `session_id`=uuid(str), V3 `chat_session.id`=BIGINT. V3는 BIGINT로 적응
  (API 응답은 web 호환 위해 문자열화 — chat 세션과 동일 패턴).

## Decision (결정)

### 1. 스트림 파서는 engine (순수), 영속·API는 domain

- **`engine/artifact/parser.py`**: V2 `ArtifactStreamParser` 이식 — 토큰 경계를 넘는 태그를 버퍼링
  (longest-suffix-prefix)하는 상태머신. `CONTENT|ARTIFACT_START|ARTIFACT_DELTA|ARTIFACT_END`
  이벤트만 방출. DB·FastAPI 무의존(ADR-0005) → engine.
- **`domains/artifact/`**: 테이블·버전·공개·데이터 CRUD(영속은 domain). chat이 파서로 분리한
  아티팩트를 END 시 여기로 영속.

### 2. chat 스트림 통합 (ADR-0011 확장)

`domains/chat/service._run`의 토큰 처리를 파서를 통해 흘린다:
- 토큰(`_chunk_text` 결과) + fake 폴백 완결본을 **파서에 feed**, 종료 시 `flush`.
- 파서 이벤트 → SSE:
  - `CONTENT` → `content {delta}` (기존).
  - `ARTIFACT_START` → chat 본문에 **칩** `\n\n[📎 title](artifact:identifier)\n\n`을 `content`로 1회 +
    `artifact_start {identifier, artifact_type, title}`.
  - `ARTIFACT_DELTA` → `artifact_delta {identifier, delta}` (chat 본문엔 안 감).
  - `ARTIFACT_END` → 아티팩트 **upsert + 새 버전 영속**, `artifact_end {identifier, version}`.
- **영속 본문 분리**: assistant 메시지에는 **칩이 포함된 display 본문**을 저장(원 아티팩트 본문은
  `artifact_version`에). 제목생성 입력(full_response)도 칩 기준(V2 동일). → `_run`이 raw `msg.content`
  대신 **파서가 만든 display 본문**을 누적·영속한다.
- 버전↔메시지 링크: 이 턴 생성된 버전 행을 저장된 assistant 메시지 id로 연결(`message_id`).

### 3. 데이터 모델 (schema llmonl) — V2 계승 3테이블

| 테이블 | 핵심 | 용도 |
|--------|------|------|
| `artifact` | id(uuid), session_id(BIGINT), user_id, identifier, artifact_type, title, current_version, is_published, public_token | 논리 아티팩트(버전 묶음) |
| `artifact_version` | id, artifact_id, version, content, message_id | 불변 스냅샷 |
| `artifact_data` | artifact_id(PK), data(JSON) | 인터랙티브 저장(`window.artifactData`) |

- FK 없음 — 연쇄 정리는 앱(세션 삭제 → 세션 아티팩트 삭제; 아티팩트 삭제 → version/data 삭제). V2 동일.
- upsert 키: `(session_id, identifier)`. 같은 identifier 재생성 시 새 버전 추가, `current_version++`.
- DDL은 init.sql + 라이브 DB 적용(기존 볼륨, ADR-0012와 동일 절차).

### 4. artifact 도메인 API (web 계약과 정렬)

`/api/v1/artifacts` — list(`?session_id=`)·get(현재 버전)·versions·get version·delete·
`POST /{id}/publish`·`GET|PUT /{id}/data`. `/api/v1/public/artifacts/{token}`(미인증) +
`/{token}/data`. 응답은 web `ArtifactSummary|Detail|VersionItem` 필드와 일치(`session_id` 문자열화).

### 5. 시스템 프롬프트 복원

Phase 0에서 트림한 **아티팩트 지시**(태그 사용법·타입·인터랙티브 저장 `window.artifactData`)를
`engine/prompts/system.md`에 복원 → 모델이 `<artifact>`를 방출하게 한다.

### 6. 하위 단계

- **3a**: DDL + `engine/artifact/parser.py` + `domains/artifact`(영속·API) + 등록. 파서 단위 테스트.
- **3b**: chat 스트림 통합(`_run` 파서 구동·칩·영속·버전링크) + system.md 복원.
- **3c**: web 재배선(`chat.ts` onArtifact·`index.tsx` store 연결·syncArtifactServerIds) — 라이브러리·패널은 기존.
- **3d(선택)**: 인터랙티브 데이터 저장 + 공개 링크(publish/public) 전체 흐름.

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| 파서를 domain에 | 순수 텍스트 변환(AI 스트림 능력) → engine. 영속만 domain. |
| 별도 tool-call로 아티팩트 생성 | 토큰 스트리밍 UX 상실(완성 후 일괄). 인라인 태그가 점진 렌더에 유리(V2 검증). |
| 아티팩트 본문을 메시지에 저장 | 메시지 비대. 칩+버전테이블 분리가 경량·버전관리 자연스러움. |
| session_id를 문자열로 저장(V2 그대로) | V3 chat_session.id=BIGINT와 불일치. BIGINT 저장 + 응답 문자열화가 일관. |
| web 아티팩트 UI 새로 작성 | 이미 완비 — 계약만 연결하면 됨. |

## Consequences (결과)

**긍정**
- 코드/문서/다이어그램을 점진 스트리밍 캔버스 + 버전관리로. web 자산 재사용(배선만).
- 파서(engine)·영속(domain) 분리로 경계 유지. ADR-0011 계약에 이벤트만 가산.

**부정 / 리스크**
- `_run`의 본문 처리(파서 구동·display 본문 영속)가 복잡해짐 — fake 폴백·HITL과 공존 주의.
- 공개 링크(public_token)는 미인증 접근 — 토큰 노출 범위·샌드박스 보안 재확인 필요(3d).
- DDL 라이브 수동 적용(기존 볼륨).

**후속**
- 3d: 인터랙티브 데이터/공개 링크. 아티팩트 sandbox 보안(web 렌더), 버전 diff, 라이브러리 검색.
