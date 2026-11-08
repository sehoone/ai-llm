# ADR-0017: 첨부 객체 스토리지 (MinIO / S3 호환)

- 상태: Accepted
- 날짜: 2026-11-08
- 결정자: sehoon
- 관련: [ADR-0014](0014-attachments-multimodal.md)(첨부/멀티모달 — §1 저장 개정), [ADR-0016](0016-document-text-extraction.md)(문서 추출), [ADR-0007](0007-llm-observability-langfuse.md)(스택 MinIO는 Langfuse 전용이었음), [ADR-0005](0005-ai-engine-layer.md)(경계)
- 참조: `deploy/docker-compose.yml`(minio 서비스), [minio-py](https://github.com/minio/minio-py), V2 `chatbot/services/file_storage_service.py`
- 로드맵: [v2-chat-migration-roadmap](../v2-chat-migration-roadmap.md) Phase 4 (ADR-0014 후속)

## Context (맥락)

ADR-0014 §1은 첨부 바이트를 **api 컨테이너 로컬 볼륨**(`UPLOAD_DIR=/data/uploads`)에 저장하고, S3/MinIO는
"다중 인스턴스 전환 시 후속 어댑터"로 미뤘다. 요구가 바뀌어 **업로드 파일은 MinIO에 저장**해야 한다.
로컬 볼륨은 api 인스턴스에 묶여 수평 확장·재배치 시 파일이 흩어지고, 백업·수명주기 관리가 어렵다.

스택에는 이미 MinIO가 있으나 **Langfuse 전용**이다(버킷 `langfuse-events`·`langfuse-media`·
`langfuse-exports`, 내부 `minio:9000`, 콘솔만 `127.0.0.1:${MINIO_PORT}` 노출 — `docker-compose.yml:156`).
이 ADR은 ADR-0014 §1(저장)·§4(다운로드)를 개정해 첨부를 MinIO에 저장한다. 다른 결정(§2 base64 전송,
§3 멀티모달 구성, ADR-0016 추출)은 그대로다.

## Decision (결정)

### 1. 저장 = MinIO 전용 버킷 (ADR-0014 §1 개정)

첨부 바이트를 MinIO 버킷 `chat-attachments`(Langfuse 버킷과 분리)에 저장하고, 메타(`chat_attachment`)만
DB(llmonl)에 둔다 — 메타/바이트 분리 원칙은 ADR-0014 유지. MinIO는 S3 호환이므로 **클라우드 S3로
엔드포인트/자격만 바꿔 전환 가능**(어댑터 교체 없이 설정).

### 2. 오브젝트 키 = 기존 `storage_path` 재사용 (스키마 변경 없음)

`chat_attachment.storage_path`는 이미 `"{session_id}/{uuid}_{sanitized}"` 상대경로다. 이를 **오브젝트
키로 그대로 사용**한다 — DB 마이그레이션 불필요. 파일명 sanitize + uuid 프리픽스(경로/키 주입 방지)도
ADR-0014 그대로.

### 3. `core/storage` = 객체 스토리지 어댑터 (인터페이스 안정)

`FileStorage`의 공개 계약(`save_base64`·`delete` + 신규 `open_stream`)을 유지해 도메인(`ChatService`)
변경을 최소화하고, 구현만 로컬 디스크 → MinIO로 바꾼다. 로컬 전용이던 `absolute_path(Path)`는
객체 스토리지에 맞지 않으므로 **제거하고 바이트 스트림 반환으로 대체**한다.

- 클라이언트: **`minio` 파이썬 SDK**(경량·목적특화). boto3는 더 무겁고 범용 — 대안 표 참조.
- 기동 시 버킷 보장: 없으면 `make_bucket`(Langfuse가 entrypoint `mkdir`로 버킷을 만드는 것과 동일 취지).
- `save_base64`: base64 디코드 → 크기 검증(ADR-0014 §5, 10MB) → `put_object(bucket, key, data, size,
  content_type)`. (크기·content_type 메타를 오브젝트에 함께.)

### 4. 다운로드 = 백엔드 프록시 스트림 (ADR-0014 §4 개정)

MinIO 9000은 브라우저에 노출되지 않는다(내부망). 따라서 presigned URL이 아니라 **백엔드가 객체를
스트리밍 프록시**한다 — `GET /chat/attachments/{id}`가 소유자/관리자 인가(ADR-0014 §4 유지) 후
`get_object`로 받은 바이트를 `StreamingResponse`로 내려준다(`Content-Type`·`Content-Disposition` 세팅).
기존 `FileResponse(path=…)`를 대체.

### 5. 삭제 = 세션 정리 시 오브젝트 제거

세션 삭제 시 첨부 메타(repo)와 함께 각 오브젝트를 `remove_object`로 지운다(ADR-0014 §4의 앱 정리 유지).
로컬 `unlink`를 대체.

### 6. 설정 + 배포

`core/config`에 추가: `minio_endpoint`(기본 `minio:9000`), `minio_access_key`·`minio_secret_key`
(`MINIO_ROOT_*` 재사용 또는 전용 자격), `minio_bucket`(기본 `chat-attachments`), `minio_secure`
(기본 False — 내부 http). `storage_backend`(`minio`|`local`, 기본 `minio`)로 **bare 로컬 개발
(docker 없이 `uv run poe dev`)에서는 로컬 디스크로 폴백** — 어댑터 선택 seam. compose의 api 서비스에
MinIO 환경변수 추가, `depends_on: minio`.

### 7. 추출(ADR-0016)과의 관계 — 변화 없음

추출은 **전송 시점**에 요청 본문의 base64 바이트에서 수행하므로 MinIO를 읽지 않는다(ADR-0016 §3 유지).
이력 메시지의 재추출(스토리지에서 GET)은 후속.

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| 로컬 볼륨 유지 (ADR-0014) | 요구 변경. api 인스턴스 종속 — 수평 확장·재배치·백업에 불리. |
| Langfuse 버킷 공유 | 수명주기·권한·목적이 다름. 전용 버킷이 격리·정리에 안전. |
| boto3 | S3 범용이나 의존성 무겁고 API 장황. MinIO SDK가 이 용도엔 간결. (클라우드 S3도 minio SDK가 지원) |
| presigned URL 다운로드 | MinIO 9000이 브라우저에 비노출(내부망). 노출 시 인가 우회·CORS 부담. 프록시가 인가 일관. |
| storage_path 스키마 변경(버킷/키 분리 컬럼) | 기존 상대경로가 키로 그대로 유효 — 마이그레이션 불필요. |

## Consequences (결과)

**긍정**
- 첨부가 인스턴스 비종속 — 수평 확장·재배치에 견고. S3 호환이라 클라우드 전환은 설정만.
- 메타/바이트 분리·인가·정리 흐름은 ADR-0014 유지, 어댑터 인터페이스 안정으로 도메인 변경 최소.
- 스택의 MinIO 재사용(신규 인프라 없음), Langfuse와 버킷 격리.

**부정 / 리스크**
- MinIO 의존 추가 — bare 로컬 개발은 `storage_backend=local` 폴백 필요.
- 다운로드가 백엔드를 경유(프록시) — 대용량 다수 다운로드 시 api 대역 소비. (10MB 상한으로 완화)
- 자격·버킷 정책·네트워크(내부 http) 운영 고려 추가.

**후속**
- 클라우드 S3 전환(설정), presigned URL(브라우저 노출 시), 이력 재추출용 스토리지 GET,
  오브젝트 수명주기/버저닝, 서버측 암호화.
