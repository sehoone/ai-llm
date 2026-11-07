# ADR-0014: 첨부 / 멀티모달 (이미지 비전 + 텍스트, 로컬 저장)

- 상태: Accepted
- 날짜: 2026-11-07
- 결정자: sehoon
- 관련: [ADR-0011](0011-chat-streaming-contract.md)(chat 입력), [ADR-0010](0010-engine-llm-provider.md)(모델), [ADR-0005](0005-ai-engine-layer.md)(경계)
- 참조: V2 `chatbot/services/file_storage_service.py`·`models/attachment_model.py`, `common/services/graph.py`(멀티모달 구성), `chatbot/schemas/chat_schema.py`
- 로드맵: [v2-chat-migration-roadmap](../v2-chat-migration-roadmap.md) Phase 4

## Context (맥락)

사용자가 chat에 이미지·텍스트 파일을 첨부하면, 이미지는 **비전**으로 모델이 보고, 텍스트는 내용이
프롬프트에 포함되어야 한다. web은 이미 첨부 UI(ChatInput 업로드·`chat-area` 렌더·download 버튼,
`FileAttachment`/`AttachmentMeta` 타입)를 갖췄다. V3 chat은 Phase 1에서 파일 처리를 떼어냈고 백엔드
첨부가 없다.

V2 방식: user 메시지에 파일이 있으면 LangChain 메시지 `content`를 **블록 리스트**로 구성 — 텍스트
블록 + 이미지(`{"type":"image_url","image_url":{"url":"data:<ct>;base64,<data>"}}`) + 텍스트파일(추출
텍스트). 파일 바이트는 **로컬 디스크**(UPLOAD_DIR)에 저장하고 메타만 DB에. (MinIO는 스택에서 Langfuse
전용·내부 9000.)

## Decision (결정)

### 1. 저장 = 로컬 볼륨 (V2 계승)

파일 바이트는 api 컨테이너의 마운트 볼륨(`UPLOAD_DIR=/data/uploads`)에 저장, 메타(`chat_attachment`)만
DB(llmonl). S3/MinIO는 다중 인스턴스 전환 시 후속(어댑터 교체 지점). 저장 경로는 `base_dir` 상대경로로
저장해 재배치 가능. 파일명은 sanitize + uuid 프리픽스(경로 주입 방지).

### 2. 전송 = 메시지 본문에 base64 (멀티파트 아님)

`POST /sessions/{id}/messages` 본문에 `files: [{filename, content_type, data(base64)}]`를 싣는다
(V2 non-stream과 동일, 스트리밍 응답과 무관). 멀티파트 업로드는 불필요한 복잡도.

### 3. 멀티모달 그래프 입력 (domain이 구성)

파일이 있으면 도메인이 그래프 입력 `HumanMessage.content`를 **블록 리스트**로 만든다:
- 텍스트 블록(사용자 메시지 + RAG 컨텍스트, ADR-0012와 합성),
- 이미지 → `image_url` data URI 블록(비전),
- 텍스트 파일 → 추출 텍스트 블록,
- **PDF → placeholder 텍스트**(V2와 동일 — 추출 미구현, pypdf 후속).

engine 모델(`LlmChatModel`→ChatLiteLLM)은 리스트 content를 그대로 전달(gpt-4o 계열 비전 지원). 영속·표시용
메시지 본문은 **텍스트만**(첨부는 `chat_attachment`), 멀티모달 리스트는 그래프 입력에만.

### 4. 영속·조회·다운로드

- 첨부는 **user 메시지**에 연결(`chat_attachment.message_id`). 업로드 시 파일 저장 + 메타 insert.
- `GET /sessions/{id}/messages`가 메시지별 첨부 메타(`AttachmentMeta`)를 함께 반환(배치 조회).
- `GET /chat/attachments/{id}` 다운로드 — **소유자 또는 관리자**(세션 소유 확인). `FileResponse`.
- 세션 삭제 시 첨부 메타·파일도 정리(FK 없음 — 앱 정리).

### 5. 지원 타입 (V2 계승)

이미지 `image/{jpeg,png,gif,webp}`(비전) · 텍스트 `text/{plain,markdown,csv}`·`application/json`(추출) ·
`application/pdf`(placeholder). 최대 10MB/파일.

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| MinIO/S3 저장 | S3 클라이언트·버킷·엔드포인트 선지불. V2는 로컬. 다중 인스턴스 전환 시 어댑터로 후속. |
| 멀티파트 업로드 | 스트리밍 POST와 별도 엔드포인트·흐름. base64 본문이 단순(V2 동일). |
| 멀티모달 구성을 engine에 | FileAttachment는 도메인 입력. 도메인이 메시지 값 구성, engine은 전달(ADR-0005). |
| PDF 텍스트 추출 | pypdf 의존·레이아웃 이슈. V2도 미구현 — placeholder로 두고 후속. |

## Consequences (결과)

**긍정**
- 이미지 비전 + 텍스트 첨부로 멀티모달 chat. web 자산 재사용(배선만). 의존성 추가 없음.
- 저장 어댑터 분리로 S3 전환 경로 확보.

**부정 / 리스크**
- 로컬 볼륨 — 다중 인스턴스에선 공유 스토리지/ S3 필요(후속).
- PDF 미추출(placeholder). base64는 큰 파일에서 요청 비대(10MB 상한).
- 비전 비용·토큰 증가(이미지).

**후속**
- PDF 추출(pypdf), S3/MinIO 어댑터, 이미지 리사이즈/썸네일, 스트리밍 멀티파트.
