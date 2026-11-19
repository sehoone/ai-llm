# ADR-0022: 커넥터 — 챗 도구를 사내 MCP 서버로 확장 (connector 도메인 + engine MCP 로더)

- 상태: Accepted
- 날짜: 2026-11-19
- 결정자: sehoone
- 관련: [ADR-0008](0008-chat-human-approval.md) (챗 승인 — MCP 도구가 RiskTier/HITL로 게이트) · [ADR-0005](0005-ai-engine-layer.md) (engine↔domain 경계 — 도구 로드는 engine, 인가는 domain) · [ADR-0021](0021-projects.md) (프로젝트 — 활성 커넥터 집합 보유) · [ADR-0018](0018-env-config-layout.md) (비밀 분리 — sk- 키 참조) · [ADR-0020](0020-user-portal-frontend.md) (포털 — 커넥터 UI·데이터 스코핑)

## Context (맥락)

claude.ai 컴포저에는 **커넥터(Connectors)** 가 있다 — 외부 시스템 능력을 챗에 붙이는 기능이며 **MCP(Model Context Protocol)** 기반이다. 포털 컴포저(`composer.tsx`)는 현재 `ModelSelector`·`RagSelector`만 있고 커넥터가 없다.

이 아키텍처에는 커넥터의 연결 지점이 **이미 예약**돼 있다:

- `chat/service.py`가 `default_registry()`(샘플 도구 4개) → `ApprovalPolicy` → 그래프로 **HITL 승인(ADR-0008)이 라이브**다. 도구만 데모이고, `engine/agent/tools.py`는 *"실제 도구(MCP 연동)는 도메인 이식 단계에서 교체"*라고 교체 지점을 명시한다.
- `engine/agent/registry.py`의 `ToolRegistry`/`ToolSpec`/`RiskTier`(AUTO/CONFIRM/BLOCK)가 도구 추상과 위험도를 이미 정의한다.
- 조직에 **`mcp-platform`**(별도 리포)이 있다 — `platform-server`(사용자별 `sk-` 키 발급·검증), `spring-ai-mcp`(`/mcp` SSE 엔드포인트, `Bearer sk-` 검증). 즉 사내 MCP 서버 인프라가 가동 중이다.

→ 커넥터의 백엔드는 **사내 mcp-platform**로 정한다(외부 OAuth 커넥터는 범위 외·후속).

## Decision (결정)

### 1. 커넥터 = 사내 MCP 서버 등록. engine/agent에 MCP 로더 추가

`engine/agent`에 MCP 로더를 둔다: **MCP 서버 좌표 + `sk-` 인증**을 받아 그 서버의 tool 목록을 `ToolSpec`으로 래핑(각 MCP tool → `handler`)해 반환한다. 외부 부수효과이므로 기본 `RiskTier=CONFIRM`(ADR-0008 §1 보수적 기본) — 큐레이션으로만 AUTO 승격.

"도구를 로드하고 위험도를 매기는 것"은 AI 능력이므로 engine(ADR-0005). engine은 domains·FastAPI를 import하지 않고, **MCP 서버 좌표·토큰을 도메인에서 주입**받는다.

### 2. 새 도메인 `domains/connector/` (수직 슬라이스)

"어떤 커넥터가 누구에게 켜졌는가"(인가·영속)는 domain이 소유한다.

**테이블 `llmonl.connector`**:

```
id TEXT PK · user_id BIGINT · name · description
mcp_url TEXT            -- spring-ai-mcp /mcp 좌표
credential_ref TEXT     -- sk- 키 참조(평문 금지, 비밀 저장소/참조)
enabled BOOL DEFAULT true
created_at · updated_at
```

**라우터 `/api/v1/connectors`** (`ApiResponse[T]`): CRUD + `GET /{id}/tools`(로드된 도구 목록 미리보기) + enable/disable.

### 3. chat 연동 — per-request 레지스트리 합성

`ChatService`가 요청마다 레지스트리를 **베이스 ∪ 활성 커넥터 도구**(사용자 + 활성 프로젝트(ADR-0021))로 조립해 그래프에 주입한다. `ApprovalPolicy`/HITL은 그대로 — 새 승인 체계 불필요.

### 4. 프로젝트·컴포저 연동 — claude.ai 인터페이스 참고

claude.ai 컴포저는 입력창 하단에 첨부(+)·커넥터·스킬 칩과 모델 선택·전송 버튼을 둔다. 포털 `composer.tsx`(현재 `ModelSelector`·`RagSelector`만)에 **Connectors·Skills(ADR-0024)** 칩을 나란히 추가한다.

```
컴포저 (claude.ai 참고):
┌────────────────────────────────────────────────────┐
│  메시지를 입력하세요…                                 │
│                                                      │
│  [+]  [🔌 커넥터]  [✦ 스킬]      [Claude Sonnet ⌄] [↑]│
└────────────────────────────────────────────────────┘
       │            │
       │            └─ 스킬 팝오버 (ADR-0024)
       └─ 첨부 / 커넥터 추가

커넥터 팝오버 (활성 커넥터 on/off · 대화별):
┌──────────────────────────┐
│ 커넥터                    │
│ ☑ 사내 위키 MCP           │
│ ☑ Jira MCP                │
│ ☐ 코드검색 MCP            │
│ ────────────────────────│
│ + 커넥터 추가 (MCP 서버)  │
└──────────────────────────┘
```

- **프로젝트(ADR-0021)**: 프로젝트가 **기본 활성 커넥터 집합**을 핀으로 보유 → 그 프로젝트 대화는 해당 커넥터 자동 적용(프로젝트 홈 우측 패널의 "활성 스킬·커넥터").

### 5. 보안

- `sk-` 키는 **DB 평문 금지** — mcp-platform이 사용자별 발급하므로 `credential_ref`로 참조 보관(ADR-0018 비밀 분리).
- 커넥터 등록·조회는 `user_id` 소유권 스코핑(ADR-0020 §3 — IDOR 방지).
- MCP 도구는 외부 부수효과 → 기본 CONFIRM(HITL 경유).

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **사내 mcp-platform MCP 로드** (채택) | 기존 MCP 자산·sk- 키·HITL 즉시 재사용, 교체 지점 실현 | MCP 런타임 의존(연결·지연 처리 필요) |
| 외부 OAuth 커넥터(Drive/Gmail) 직접 | claude.ai 패리티 | OAuth 토큰 인프라 신규, 사내 MCP 미활용. MCP 추상으로 후속 수용 가능 |
| 정적 하드코딩 도구 확장 | 단순 | 사용자/프로젝트별 확장 불가 — 커넥터 개념 불성립 |
| chat 도메인에 커넥터 상태 포함 | 테이블 1개 절약 | 재사용·스코핑·프로젝트 공유 어려움. 별도 도메인이 경계 명확 |

## Consequences (결과)

**긍정**
- 사내 MCP 자산을 즉시 챗 도구로 활용, HITL(ADR-0008) 재사용, 데모 레지스트리 교체 지점 실현.
- MCP 표준이라 향후 외부 커넥터로 일반화 여지.
- 도구 로드(engine)와 인가(domain) 경계가 ADR-0005/0008 분담과 일치.

**부정 / 리스크**
- MCP 런타임 의존 — 연결 실패·타임아웃·도구 스키마 변동 처리 필요(로드 캐시·degrade).
- `sk-` 키 수명·스코프 관리(만료·폐기) 부담.
- 외부 도구 기본 CONFIRM → 승인 빈도↑. per-tool 위험 큐레이션(AUTO 승격) 정책/UI 필요.
- 커넥터 도구가 프로젝트 지식·메모리와 겹칠 때 우선순위 혼선 가능.

**후속 작업 / 미결**
- 외부 OAuth 커넥터(Drive/Gmail 등) — 일반 MCP 추상 위에서 후속 ADR.
- per-tool 위험 티어 큐레이션 UI, 도구 결과 캐시.
- MCP 서버 헬스체크·재시도, sk- 키 자동 폐기 연동(mcp-platform).
