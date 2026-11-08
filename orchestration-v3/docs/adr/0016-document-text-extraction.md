# ADR-0016: 문서 본문 추출 (engine/extraction — markitdown)

- 상태: Accepted
- 날짜: 2026-11-08
- 결정자: sehoon
- 관련: [ADR-0014](0014-attachments-multimodal.md)(첨부/멀티모달), [ADR-0011](0011-chat-streaming-contract.md)(chat 입력·SSE), [ADR-0005](0005-ai-engine-layer.md)(엔진 경계), [ADR-0012](0012-engine-rag.md)(후속 — 인제스트 추출기 공유)
- 참조: [markitdown](https://github.com/microsoft/markitdown)(MS, 다포맷 → markdown), V2 `chatbot/services/file_storage_service.py`
- 로드맵: [v2-chat-migration-roadmap](../v2-chat-migration-roadmap.md) Phase 4 (ADR-0014 후속)

## Context (맥락)

ADR-0014로 chat 첨부/멀티모달이 구현됐다. 그러나 **문서 본문 추출이 빠져 있어** 사용자가 파일을
올려도 모델이 내용을 읽지 못한다:

- 이미지(`image/*`) → 비전 블록으로 모델이 본다. ✅
- 텍스트(`text/*`·`application/json`) → base64 디코드해 텍스트 블록. ✅
- **PDF → placeholder**(`[PDF attached: ... Content extraction not implemented.]`) — 모델이 못 읽음. ❌
- **그 외(docx·xlsx·pptx 등) → `ALL_SUPPORTED_TYPES`에 없어 400 거부.** ❌

게다가 web 파일 입력(`chat-input.tsx`)에 `accept`·검증이 없어 사용자는 아무 파일이나 올릴 수 있는데,
백엔드는 PDF는 placeholder·나머지는 400으로 막는다 → "업로드해도 처리 안 됨". ADR-0014 "후속"에도
`PDF 추출(pypdf)`이 명시돼 있다. 이 ADR은 그 후속을 문서·Office 전반으로 일반화한다.

## Decision (결정)

### 1. 추출 능력 = `engine/extraction` 신규 모듈 (ADR-0005 경계)

바이트→텍스트 변환은 재사용 가능한 능력이므로 engine에 둔다(`engine/transcription` 오디오→텍스트와
동일 성격의 선례). `domains`·FastAPI를 import하지 않아 import-linter 계약(`domains→engine→core`)을
그대로 만족한다. 공개 API는 단일 진입점:

```
engine/extraction/
├─ __init__.py       # extract_text(data, content_type, filename) -> ExtractResult
└─ markitdown.py     # markitdown 어댑터 (지연 import)
```

```python
@dataclass(frozen=True)
class ExtractResult:
    text: str
    status: Literal["ok", "empty", "truncated", "unsupported"]
    note: str | None = None   # "스캔 PDF 추정 — 텍스트 레이어 없음" 등
```

### 2. 추출기 = markitdown (단일 라이브러리 다포맷)

Microsoft `markitdown`으로 PDF·docx·xlsx·pptx·html 등을 **markdown으로 통합 변환**한다. 포맷별
라이브러리를 개별 배선하지 않고 하나의 어댑터로 처리 — 지원 포맷 확장이 디스패치 추가 없이 가능.
markdown 출력은 LLM 입력에 자연스럽고 표·제목 구조를 보존한다. 무거운 의존성(추이적)은 받아들인다
(대안 표 참조). import는 모듈 로드 지연으로 두어 미사용 시 비용을 피한다.

### 3. 도메인은 placeholder 대신 추출 호출 (ADR-0014 §3 유지)

멀티모달 블록 구성은 여전히 **도메인**(`_build_graph_content`)이 소유하고, engine은 바이트→텍스트만
반환한다. PDF/문서 분기를 교체:

```python
else:  # 이미지·단순텍스트 외 문서 → engine 추출
    raw = base64.b64decode(f.data)
    res = extract_text(raw, f.content_type, f.filename)
    parts.append({"type": "text", "text": _render_extracted(f.filename, res)})
```

영속·표시용 메시지 본문은 여전히 **텍스트만**(첨부 바이트는 `chat_attachment`), 추출 텍스트는
그래프 입력 블록에만 싣는다. 추출은 **전송 시점**에 수행한다(바이트가 요청에 있음) — 별도 영속 불필요.

### 4. 컨텍스트 폭주 방지 — 상한 + truncate

10MB 문서는 수백 페이지가 될 수 있다. `settings`에 상한을 두고 초과 시 잘라 `status="truncated"`로
표시(렌더 블록에 "…(이하 생략)" 표기):

- `max_extract_chars`(기본 ~50_000자) — 초과분 절단.
- 추출 결과가 비면(스캔 PDF 등) `status="empty"` → 모델에 "추출 불가(스캔 이미지 가능성)" 안내 블록.
  OCR은 후속.

### 5. 지원 타입 확장 + 스트림 전 검증 (기존 버그 수정)

- `schema.py`의 지원 타입에 Office(`docx`/`xlsx`/`pptx`) MIME을 추가하고, 추출은 markitdown이 포맷을
  판별하므로 content_type 디스패치는 "이미지 / 단순텍스트 / 그 외(추출)"의 3분기로 단순화한다.
- **검증을 스트림 시작 전으로 이동**: 현재 `_persist_attachments`가 StreamingResponse 제너레이터
  **내부**에서 `HTTPException`을 raise해 400이 정상 전달되지 않는다. 타입/크기 검증을 라우트
  (`send_message`)에서 스트림 시작 전에 수행해 깔끔한 400을 반환한다.

### 6. web — `accept` + 클라이언트 검증 (UX)

파일 입력 `accept`를 백엔드 지원 타입과 일치시키고, 미지원 타입·크기 초과는 즉시 toast로 피드백해
"올렸는데 아무 일도 안 일어남"을 제거한다.

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| pypdf만 (PDF 전용) | 가장 가볍지만 Office를 못 읽음. 포맷마다 라이브러리·분기 증식. 사내 문서가 Office 중심. |
| 포맷별 라이브러리 조합(python-docx·openpyxl·python-pptx·pypdf) | 의존성 N개 + 포맷별 추출 코드·엣지 케이스를 직접 관리. markitdown이 이를 흡수. |
| `unstructured` | 더 강력하지만 ML 의존성·설치 부담이 markitdown보다 큼. |
| 업로드 시 추출해 영속 | 전송 시점에 바이트가 이미 있어 불필요. 이력 재전송도 없음(단발 첨부). |
| 추출을 domain에 인라인 | 재사용(RAG 인제스트)·경계(ADR-0005) 위배. engine 모듈이 정합. |

## Consequences (결과)

**긍정**
- PDF·Office 본문을 모델이 실제로 읽는다. 단일 어댑터로 포맷 확장 용이.
- engine 격리 유지 — RAG 인제스트(ADR-0012)가 동일 추출기를 재사용할 경로 확보.
- 스트림 전 검증으로 첨부 오류가 올바른 400으로 전달(기존 제너레이터 내 raise 버그 수정).

**부정 / 리스크**
- markitdown 추이적 의존성이 무겁다(설치 용량·빌드 시간). 지연 import로 런타임 비용은 완화.
- 스캔 PDF는 텍스트 레이어가 없어 추출 불가(empty) — OCR 후속.
- 큰 문서는 truncate로 정보 손실 가능. 상한은 설정으로 조정.

**후속**
- 스캔 PDF OCR, RAG 인제스트와 추출기 공유(ADR-0012 연계), 추출 캐시, S3 스토리지(ADR-0014 후속).
