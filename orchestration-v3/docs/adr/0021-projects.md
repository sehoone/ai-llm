# ADR-0021: 프로젝트 — 대화·지침·지식 작업공간 (project 도메인)

- 상태: Accepted
- 날짜: 2026-11-19
- 결정자: sehoone
- 관련: [ADR-0008](0008-chat-human-approval.md) (chat 승인 그래프 — 프로젝트 대화가 재사용) · [ADR-0011](0011-chat-streaming-contract.md) (chat 스트리밍 계약 재사용) · [ADR-0012](0012-engine-rag.md) (RAG — 프로젝트 지식베이스의 기반) · [ADR-0013](0013-artifacts.md) (아티팩트 — 프로젝트 세션 산출물 집계) · [ADR-0020](0020-user-portal-frontend.md) (사용자 포털 — 프로젝트 UI가 올라가는 앱 셸) · [ADR-0022](0022-connectors-mcp.md) (커넥터 — 프로젝트가 활성 커넥터 집합 보유) · [ADR-0024](0024-skills-instruction-presets.md) (스킬 — 프로젝트가 기본 스킬 집합 보유)

## Context (맥락)

claude.ai의 **Project**(`claude.ai/cowork/projects`)는 하나의 작업공간에 네 가지를 묶는다:

1. **대화 묶음** — 관련 대화를 한 프로젝트 아래 모은다.
2. **공유 지침(custom instructions)** — 프로젝트의 모든 대화에 적용되는 system prompt.
3. **전용 지식(project knowledge)** — 업로드한 문서가 프로젝트 대화에서 자동 검색된다.
4. **산출물** — 프로젝트 대화에서 생성된 아티팩트.

포털(ADR-0020)에는 이 조각들이 **이미 전부** 구현되어 있다:

| Project 요소 | 기존 자산 |
|---|---|
| 대화 묶음 | `chat_session`/`chat_message` — HITL(0008)·스트리밍(0011)·첨부(0014·0017)·재생성·메모리(0015) 포함 |
| 공유 지침 | `custom_gpt.instructions` 패턴(gpts 도메인) — system prompt 주입 |
| 전용 지식 | `rag_group_config`/`document`/`rag_embedding` — pgvector·문서추출(0016) |
| 산출물 | `artifact.session_id` — 세션별 아티팩트 |

따라서 결정의 본질은 "무엇을 새로 만드느냐"가 아니라 **"이 조각들을 어떻게 묶느냐"**다.

핵심 선택지는 대화 엔진이다. gpts 도메인은 이미 "사용자 정의 지침 + 지식"을 가지지만, **도구·HITL·아티팩트가 없는 단순 Q/A**(엔진 `LlmChatModel.stream` 직접 호출)로 구현되어 있다. 프로젝트 대화를 gpts 경로로 올리면 claude.ai Project의 풀 대화 경험(도구 승인·아티팩트·첨부)을 재현할 수 없다.

## Decision (결정)

### 1. 프로젝트 대화는 **chat 스택을 재사용**한다 (gpts 병렬 스택 아님)

프로젝트 대화는 일반 chat 대화와 동일한 엔진(ADR-0008 승인 그래프 · 0011 스트리밍 · 0013 아티팩트 · 0014 첨부 · 0015 메모리)을 그대로 쓴다. 차이는 **컨텍스트 주입**뿐이다.

- `chat_session`에 **nullable `project_id`** 컬럼을 추가한다(비정규화 — FK 없이 chat/gpts 관례 계승).
  - `project_id IS NULL` = 일반 대화(현행 동작 불변).
  - `project_id` 설정됨 = 프로젝트 소속 대화.
- `ChatService`에 두 지점만 보강한다:
  1. **`create_session(user, title, project_id=None)`** — 세션 생성 시 소속 프로젝트 기록.
  2. **`stream_message(...)`** — 세션에 `project_id`가 있으면
     ① `project.instructions`를 그래프 **system prompt**로 prepend,
     ② 요청이 `rag_group`을 명시하지 않으면 **프로젝트의 `rag_group`으로 자동 설정**(지식 자동 검색).

→ HITL·스트리밍·아티팩트·첨부·재생성이 **추가 엔진 코드 없이** 프로젝트 대화에서 동작한다.

### 2. 프로젝트 지식베이스는 **engine/rag 재사용**한다

프로젝트는 생성 시 **전용 `rag_group`/`rag_key`를 프로비저닝**한다(`rag_group_config`에 프로젝트 1:1 그룹 1개). 지식 파일 업로드·목록·삭제는 `rag` 도메인 로직을 프로젝트의 `rag_key`로 스코핑해 재사용한다 — 문서추출(0016)·청킹·임베딩·pgvector 검색(0012)을 그대로 쓰고 **새 임베딩 코드는 없다**.

### 3. 새 도메인 `domains/project/` (수직 슬라이스)

CLAUDE.md 규칙대로 `api·service·repository·schema·model` 슬라이스 + `main.py` 라우터 등록. AI 연산은 전부 chat·engine/rag에 위임하므로 **`engine/` 추가는 없다**.

**테이블 `llmonl.project`** (uuid PK — gpts/rag 관례):

```
id TEXT PK · user_id BIGINT · name · description · instructions TEXT DEFAULT ''
rag_key TEXT · rag_group TEXT   -- 전용 지식베이스(1:1)
icon TEXT DEFAULT 'folder' · color TEXT DEFAULT '#6366f1'
created_at · updated_at
```

**`chat_session` 변경**: `ADD COLUMN IF NOT EXISTS project_id TEXT`(+ 인덱스). `thread_rev` 선례와 동일한 재실행-안전 ALTER.

연쇄 정리는 FK 없이 repository가 명시 수행(프로젝트 삭제 → 소속 세션·메시지·지식 문서·임베딩 정리).

**라우터 `/api/v1/projects`** (`ApiResponse[T]` 래핑):

```
POST   /projects                       생성(rag_group 자동 프로비저닝)
GET    /projects                       내 목록
GET    /projects/{id}                  상세
PUT    /projects/{id}                  이름·설명·지침 수정
DELETE /projects/{id}                  프로젝트+세션+지식 연쇄 삭제
GET    /projects/{id}/sessions         소속 대화(chat_session WHERE project_id)
POST   /projects/{id}/sessions         프로젝트 안 새 대화 → ChatService.create_session(project_id)
GET    /projects/{id}/knowledge        지식 문서 목록
POST   /projects/{id}/knowledge        업로드 → engine/extraction + engine/rag
DELETE /projects/{id}/knowledge/{doc}  문서 삭제
GET    /projects/{id}/artifacts        세션들의 아티팩트 집계(조회 전용)
```

### 4. 포털 UI — claude.ai 사용자 인터페이스 참고 (ADR-0020 앱 셸)

claude.ai(`claude.ai/cowork/projects`) 레이아웃을 참고한다. 와이어프레임은 참고용이며 포털 디자인시스템(ADR-0020)으로 구현한다.

- **사이드바**: `chat-sidebar.tsx` NAV 위에 "프로젝트" 섹션 추가(claude.ai 순서 — 프로젝트 → 채팅 → 아티팩트 → 최근 대화).

```
┌─────────────────────┐
│  ✦ AI 포털           │
│  [   + 새 대화    ]  │
│                     │
│  📁 프로젝트      ▸  │  ← 신규 (클릭 → /projects)
│  💬 채팅            │
│  ✦ 아티팩트         │
│                     │
│  최근 대화           │
│  · 마케팅 기획안     │
│  · API 설계 리뷰     │
│  · …                │
│ ─────────────────── │
│  👤 sehoone      ⌄  │
└─────────────────────┘
```

- **`/projects`** — 프로젝트 카드 그리드(gpts 페이지 UI 재사용).

```
┌────────────────────────────────────────────────┐
│  프로젝트                       [ + 새 프로젝트 ] │
│  대화·지침·지식을 한 작업공간에 모으세요           │
│                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │ 📁 마케팅   │ │ 📁 백엔드   │ │ 📁 리서치   │   │
│  │ 캠페인 기획  │ │ API 설계    │ │ 경쟁사 분석  │   │
│  │ 대화 12·3일전│ │ 대화 5·어제 │ │ 대화 2·방금  │   │
│  └────────────┘ └────────────┘ └────────────┘   │
└────────────────────────────────────────────────┘
```

- **`/projects/[id]`** — 프로젝트 홈. claude.ai처럼 좌측=대화 시작+소속 대화, 우측=지식·지침 패널.

```
┌───────────────────────────────┬───────────────────────┐
│  📁 마케팅 캠페인        ⚙ 편집 │  프로젝트 지식          │
│  Q4 런칭 캠페인…               │  [ + 콘텐츠 추가 ]      │
│                               │  ▣ 브랜드가이드.pdf     │
│  ┌─────────────────────────┐  │  ▣ 시장조사.docx       │
│  │ 새 대화 시작…           │  │  ▢ 지식 사용량 12%      │
│  │ [ 메시지 입력…       ↑ ]│  │ ───────────────────── │
│  └─────────────────────────┘  │  프로젝트 지침          │
│                               │  ┌───────────────────┐ │
│  이 프로젝트의 대화            │  │ 당신은 마케팅…     │ │
│  · 런칭 슬로건 브레인스토밍    │  │ (system prompt)   │ │
│  · 타깃 페르소나 정의          │  └───────────────────┘ │
│  · …                         │  활성 스킬·커넥터    ▸  │
└───────────────────────────────┴───────────────────────┘
```

- **`/chat`** — 기존 화면 재사용. `activeProjectId`가 있으면 상단에 프로젝트 배지 표시 + `project_id`로 세션 생성.
- `src/api/projects.ts`(gpts.ts 패턴), `chat-store.ts`에 `activeProjectId` 추가.

### 5. gpts와의 관계 — 공존

- **GPTs** = 공유 가능한 봇(단순 Q/A, `is_public`). **Project** = 내 작업공간(풀 대화 + 지식 + 지침).
- 지침·지식 개념이 겹치지만 대화 엔진·공유 모델·대상 사용자가 다르므로 통합하지 않는다. 향후 중복이 커지면 "지침+rag_key" 공통 부분 추출을 재검토(후속).

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **chat 재사용 + project 컨테이너** (채택) | HITL·아티팩트·첨부 전부 재사용, claude.ai급 대화, 최소 코드 | `ChatService`에 project 컨텍스트 분기 추가(수용 가능) |
| gpts 스택 확장(단순 Q/A) | 지침+지식 이미 존재, 구현 작음 | 도구·HITL·아티팩트 불가 — Project 경험과 괴리. 프로젝트 가치 반감 |
| gpts·project 도메인 통합 | 개념 중복 제거 | 공유 모델·대화 엔진·대상이 달라 조기 추상화. YAGNI |
| `project_id` 별도 매핑 테이블(정규화) | FK 정합성 | chat/gpts는 비정규화 비FK 관례 — 일관성 위해 컬럼 추가 채택 |

## Consequences (결과)

**긍정**
- 프로젝트 대화가 chat의 전 기능(HITL·스트리밍·아티팩트·첨부·메모리)을 **코드 추가 없이** 획득.
- 지식베이스가 engine/rag를 재사용 — 새 임베딩·검색 코드 없음.
- 새 도메인은 HTTP 경계+영속화만 담당(ADR-0005 경계 준수, engine 추가 없음).
- `project_id` nullable이라 기존 일반 대화 동작은 불변(하위 호환).

**부정 / 리스크**
- `ChatService`에 project 분기가 들어가 chat 경로가 조금 복잡해진다 — system prompt·rag_group 주입 지점을 명확히 격리해 관리.
- 지식 자동 RAG가 항상 켜지면 토큰·지연 증가 — rag_group 자동주입을 "지식이 있을 때만"으로 가드.
- gpts와 지침/지식 개념 중복 — 사용자 혼란 가능. UI 카피로 용도 구분(봇 공유 vs 작업공간).
- 데이터 스코핑(ADR-0020 §3): project·project 지식·project 세션 전부 `user_id` 소유권 필터 필수 — 누락 시 IDOR.

**후속 작업 / 미결**
- 프로젝트 공유/협업(멀티 유저) — 현 설계는 단일 소유자. claude.ai의 팀 공유는 범위 외(후속 ADR).
- 지식 자동 RAG의 토글·범위 UI(대화별 on/off).
- gpts ↔ project 공통부("지침+rag_key") 추출 재검토(중복 누적 시).
- 프로젝트 간 대화 이동(일반 대화 → 프로젝트 소속 전환) UX.
