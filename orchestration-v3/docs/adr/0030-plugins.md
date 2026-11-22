# ADR-0030: 플러그인 — 설치형 능력 번들 + 마켓플레이스 (plugin 도메인 + 거버넌스)

- 상태: Proposed
- 날짜: 2026-11-22
- 결정자: sehoone
- 관련: [ADR-0022](0022-connectors-mcp.md) (커넥터 — 플러그인이 번들하는 MCP 도구) · [ADR-0024](0024-skills-instruction-presets.md) (스킬 — 플러그인이 번들하는 지침 프리셋) · [ADR-0012](0012-engine-rag.md) (RAG — 플러그인이 번들하는 지식팩) · [ADR-0008](0008-chat-human-approval.md) (HITL — 플러그인 도구의 위험 티어/승인) · [ADR-0021](0021-projects.md) (프로젝트 — 공존하는 개인 작업공간, 플러그인과 대비) · [ADR-0020](0020-user-portal-frontend.md) (포털 — 마켓플레이스 UI·데이터 스코핑) · [ADR-0023](0023-admin-portal-split.md) (관리자/포털 분리 — 저작은 admin, 설치는 portal) · [ADR-0005](0005-ai-engine-layer.md) (engine↔domain 경계 — 플러그인은 engine 무변경)

## Context (맥락)

claude.ai의 **플러그인(`claude.ai/plugins`)** 은 능력을 하나로 묶은 **설치형 번들**이다 — skills·슬래시 명령·서브에이전트·hook·커넥터(MCP)를 묶어, 매번 컨텍스트를 다시 설명하지 않도록 역할·도구·연결을 미리 적재한다. 2026년 2월 **플러그인 마켓플레이스**가 열렸고, Team/Enterprise 관리자는 **역할별로 가용 플러그인을 관리**한다. 즉 플러그인의 본질은 세 가지다: **(1) 패키징**(여러 능력을 한 번들로), **(2) 배포**(마켓플레이스에서 탐색·설치), **(3) 거버넌스**(관리자 큐레이션·역할 가시성).

이 아키텍처에는 플러그인이 번들할 **능력 원시(primitive)가 이미 전부 구현**돼 있다:

| claude.ai 플러그인 구성 | orchestration-v3 기존 자산 |
|---|---|
| 커넥터(MCP 도구) | `connector` 도메인 + engine MCP 로더 (ADR-0022) |
| skills(지침) | `skill` 도메인 — system prompt 합성 (ADR-0024) |
| 지식 | `rag` 도메인 + engine/rag, pgvector (ADR-0012) |
| 도구 승인 | `engine/agent` 3-티어 정책 + HITL (ADR-0008) |

또한 `project`(ADR-0021)는 이 원시들을 이미 **한 작업공간에 묶는다** — 하지만 project는 **1인 소유의 사적 인스턴스**다(공유·설치·배포 개념 없음). 그래서 결정의 본질은 "능력을 새로 만드느냐"가 **아니라**:

> 이미 있는 능력 원시들을 **어떻게 패키징·배포·거버넌스하느냐.**

슬래시 명령·서브에이전트·hook은 Claude Code(개발자 CLI) 고유 개념으로 이 제품(챗 포털)에는 대응물이 없다 → **범위 밖**(ADR-0024가 정식 agent-skills를 범위 밖으로 둔 것과 동일한 선긋기). 본 결정의 플러그인은 **커넥터 + 스킬 + 지식(RAG) + 도구 정책** 네 가지를 번들한다.

## Decision (결정)

### 1. 플러그인 = 능력 원시를 **참조·합성하는 설치형 번들** (원시 재구현 아님)

플러그인은 커넥터·스킬·지식을 **직접 구현하지 않는다**. 카탈로그 수준에서 저작된 원시 정의들을 **참조**해 하나의 설치 단위로 묶을 뿐이다. 능력 실행은 전부 기존 경로(ADR-0022 커넥터 로드·0024 스킬 합성·0012 RAG 검색·0008 HITL)에 위임하므로 **`engine/` 추가는 0줄**이다. 플러그인은 **패키징·배포·거버넌스 레이어**다.

### 2. 새 도메인 `domains/plugin/` (수직 슬라이스, engine 무변경)

CLAUDE.md 규칙대로 `api·service·repository·schema·model` 슬라이스 + `main.py` 라우터 등록. AI 연산 없음(ADR-0005 경계 준수). 테이블 3종(uuid PK — gpts/connector/skill 관례):

**`llmonl.plugin`** (카탈로그 엔트리 — admin 저작):

```
id TEXT PK · name · description · icon TEXT · color TEXT
version TEXT DEFAULT '0.1.0'
status TEXT DEFAULT 'draft'          -- draft | published | deprecated
visibility TEXT DEFAULT 'all'        -- all | role:<name>  (역할별 가시성 — claude.ai 관리자 모델)
author_id BIGINT                     -- 저작 관리자
created_at · updated_at
```

**`llmonl.plugin_item`** (번들 구성 — 플러그인이 참조하는 원시):

```
id TEXT PK · plugin_id TEXT
item_type TEXT        -- connector | skill | rag | tool_policy
ref_id TEXT           -- 참조하는 connector/skill/rag_group id (카탈로그 스코프 정의)
config JSONB          -- 예: tool_policy면 {tool: 'jira.create', tier: 'AUTO'} 위험 승격
sort INT
```

**`llmonl.plugin_installation`** (사용자 설치 — 다대다):

```
id TEXT PK · plugin_id TEXT · user_id BIGINT
enabled BOOL DEFAULT true
installed_at · updated_at
UNIQUE(plugin_id, user_id)
```

FK 없이 repository가 연쇄 정리(chat/gpts/project 비정규화 관례 — ADR-0021 §3). 플러그인 삭제 → `plugin_item`·`plugin_installation` 정리.

### 3. 카탈로그 스코프 원시 — 기존 테이블에 `plugin_id` 마커 추가 (행 복제 없음)

플러그인이 번들하는 커넥터·스킬·지식은 **관리자가 카탈로그 스코프로 저작**한다. 설치 시 사용자별 행을 복제하지 않고, 기존 테이블에 **nullable `plugin_id TEXT`** 마커를 더한다(`chat_session.project_id` 선례 — 재실행-안전 `ADD COLUMN IF NOT EXISTS`):

- `connector.plugin_id` · `skill.plugin_id` · `rag_group_config.plugin_id`
  - `plugin_id IS NULL` = 현행 **사용자 소유** 원시(동작 불변).
  - `plugin_id` 설정됨 = **카탈로그 스코프** 정의. 일반 사용자 목록 쿼리(`WHERE user_id=…`)에는 **안 잡히고**, 플러그인을 **설치한** 사용자에게만 합성 시 노출된다.

이로써 능력 테이블·스코핑·엔진 주입 지점을 **그대로 재사용**하고 행 중복을 피한다.

### 4. chat 합성 — 기존 per-request 조립 지점에 "설치 플러그인" 한 항 추가

플러그인은 **새 합성 경로를 만들지 않는다**. 이미 있는 두 지점에 설치 플러그인 기여분을 **합집합**으로 더한다:

- **커넥터/도구**(ADR-0022 §3): per-request 레지스트리 = `베이스 ∪ 활성 커넥터(사용자 + 활성 프로젝트)` → 여기에 **`∪ 설치·활성 플러그인의 connector·tool_policy`** 추가. `ApprovalPolicy`/HITL(ADR-0008) 그대로. 플러그인의 `tool_policy` item이 특정 도구를 `AUTO`로 승격(큐레이션)할 수 있다.
- **스킬/지침**(ADR-0024 §2): system prompt 합성에 설치·활성 플러그인의 skill `body` 추가. 누적 우선순위에 한 단 삽입:

  ```
  베이스 system  <  project.instructions  <  설치 플러그인 skill  <  대화별 활성 스킬  <  (사용자 턴)
  ```

- **지식(RAG)**(ADR-0012·0021 §1): 플러그인이 `rag` item을 가지면 그 `rag_group`을 프로젝트 지식과 동일 방식으로 검색에 포함.

→ 순수 합성이라 **engine 코드·새 승인 체계 없음**. 플러그인은 chat의 전 기능(HITL·스트리밍·아티팩트·첨부·메모리)을 자동 획득.

### 5. 거버넌스 — 저작은 admin, 설치는 portal (ADR-0023 분리 계승)

- **라이프사이클**: `draft → published → deprecated`. `published`만 포털 마켓플레이스에 노출. `version`으로 변경 추적.
- **역할 가시성**(claude.ai 관리자 모델): `visibility`로 전체/특정 역할에만 노출. 포털 목록은 `status='published' AND (visibility='all' OR 사용자 역할 매칭)`로 필터.
- **권한**: 플러그인 저작·발행·삭제는 `require_admin`(admin). 설치·활성 토글은 일반 사용자(portal).

**라우터** (`ApiResponse[T]` 래핑):

```
# admin (저작·거버넌스) — require_admin
POST   /api/v1/plugins                     생성(draft)
GET    /api/v1/plugins                     전체 카탈로그(관리자)
PUT    /api/v1/plugins/{id}                메타·버전·status·visibility 수정
DELETE /api/v1/plugins/{id}                삭제(+item·installation 연쇄)
PUT    /api/v1/plugins/{id}/items          번들 구성(connector/skill/rag/tool_policy 참조 설정)
POST   /api/v1/plugins/{id}/publish        발행(status=published)

# portal (탐색·설치) — get_current_user
GET    /api/v1/plugins/marketplace         published + 역할 가시 목록
GET    /api/v1/plugins/{id}                상세(번들 구성 미리보기)
POST   /api/v1/plugins/{id}/install        설치(plugin_installation 생성)
DELETE /api/v1/plugins/{id}/install        제거
PUT    /api/v1/plugins/{id}/install        enabled 토글
GET    /api/v1/plugins/installed           내 설치 목록
```

### 6. 포털 UI — claude.ai/plugins 마켓플레이스 참고 (ADR-0020 앱 셸)

- **`/plugins`** — 마켓플레이스. 카드 그리드 + 설치 상태. (gpts/project 카드 UI 재사용)

```
┌──────────────────────────────────────────────────────┐
│  플러그인 마켓플레이스              🔍 검색…            │
│  능력을 번들로 설치하세요 — 커넥터·스킬·지식            │
│                                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │ 🔌 Jira 연동  │ │ ✦ 코드리뷰   │ │ 📚 사내 위키  │  │
│  │ 이슈 생성·조회│ │ 리뷰 지침+룰 │ │ 지식 검색     │  │
│  │ 커넥터·스킬   │ │ 스킬 2       │ │ 지식팩       │  │
│  │ [ 설치됨 ✓ ]  │ │ [ 설치 ]     │ │ [ 설치 ]     │  │
│  └──────────────┘ └──────────────┘ └──────────────┘  │
└──────────────────────────────────────────────────────┘
```

- **`/plugins/[id]`** — 상세: 번들 구성(커넥터·스킬·지식 목록)·버전·설치/제거. 설치 시 "포함된 도구가 챗 커넥터·스킬에 추가됨" 안내.
- **컴포저(ADR-0022 §4 / 0024 §4)**: 설치·활성 플러그인이 기여하는 커넥터·스킬이 기존 칩 팝오버에 함께 표기(출처 = 플러그인 배지). 별도 UI 불필요.
- `src/api/plugins.ts`(gpts.ts 패턴), 설치 상태는 포털 스토어.

### 7. 어드민 UI — 플러그인 저작·발행 (ADR-0023)

`apps/admin/src/features/plugins/`: 목록·CRUD·번들 구성(기존 connector/skill/rag 선택기 조합)·발행·역할 가시성·버전. 기존 admin feature(gpts·llm-resources) 패턴 재사용.

### 8. project(ADR-0021)와의 관계 — 공존·직교

- **Project** = 내 사적 작업공간(인스턴스, 1인 소유, 공유·배포 없음).
- **Plugin** = 큐레이션된 설치형 배포 패키지(1:다, 관리자 거버넌스).
- 직교한다: 프로젝트가 플러그인을 **핀으로 보유**해 그 프로젝트 대화에 자동 적용하는 것은 자연스러운 후속(§Consequences). 지금은 설치 대상 = 사용자.

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **원시 참조 번들 + 마켓플레이스/거버넌스** (채택) | 능력 재구현 0, engine 무변경, claude.ai 패리티(설치·역할 관리), project와 직교 | plugin↔원시 참조·카탈로그 스코프 스코핑 규칙 추가(수용) |
| 플러그인을 새 능력 원시로 구현 | 자체 완결 | connector/skill/rag/project와 **중복**. 유지보수·개념 폭발 |
| project 확장으로 공유·설치 추가 | 테이블 절약 | project는 1인 인스턴스 모델 — 배포·역할 거버넌스와 성격 충돌. 조기 결합 |
| 설치 시 사용자별 원시 행 복제 | 스코핑 단순(전부 user_id) | 행 중복·동기화 부담(플러그인 업데이트 시 전 설치 행 갱신). `plugin_id` 마커가 가벼움 |
| 슬래시명령·hook·서브에이전트까지 번들 | claude.ai 완전 패리티 | 챗 포털에 대응물 없음(Claude Code 고유) — 범위 밖 |

## Consequences (결과)

**긍정**
- 능력 재구현 없음 — 플러그인은 기존 connector·skill·rag·HITL을 **참조·합성만**. engine 0줄.
- chat 전 기능(HITL·스트리밍·아티팩트·첨부·메모리)을 플러그인 대화가 자동 획득(합성 지점 재사용).
- claude.ai/plugins 패리티: 마켓플레이스 탐색·설치·역할별 관리자 거버넌스.
- `plugin_id` nullable·`plugin_installation` 가산이라 기존 동작 전부 하위 호환.
- 저작(admin)/설치(portal) 분리가 ADR-0023 경계와 일치.

**부정 / 리스크**
- 합성 입력이 늘어난다(사용자 + 프로젝트 + 설치 플러그인) → 레지스트리/프롬프트 조립 복잡·토큰↑. 출처별 가드·중복 제거 필요.
- 카탈로그 스코프 원시의 **스코핑 규칙이 핵심**(ADR-0020 §3) — "설치한 사용자에게만 노출"을 어기면 IDOR/권한 누수. 설치 여부 검증을 합성·조회 양쪽에 강제.
- 플러그인 도구 `AUTO` 승격은 HITL을 우회하므로(ADR-0008) 발행 전 관리자 검토 필수 — 위험 승격은 거버넌스 게이트.
- 버전·`deprecated` 운영: 이미 설치한 사용자의 deprecated 플러그인 처리 정책 필요.
- connector/skill/rag와 "출처가 다른 같은 능력"이 겹칠 때 우선순위·중복 노출 혼선.

**후속 작업 / 미결**
- 프로젝트가 플러그인을 핀으로 보유(프로젝트 대화 자동 적용).
- 플러그인 공유 범위 확장(팀/조직 카탈로그, 설치 통계).
- 외부 OAuth 커넥터 기반 플러그인(ADR-0022 후속과 연동).
- 버전 업그레이드·마이그레이션 UX(설치본 ↔ 최신 version 차이 안내), deprecated 유예 정책.
- 플러그인 단위 관측(ADR-0007) — 어떤 플러그인/도구가 얼마나 쓰였는지.
