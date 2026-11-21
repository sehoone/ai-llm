# ADR-0024: 스킬 — 재사용 지침 프리셋 (skill 도메인 + system prompt 합성)

- 상태: Accepted
- 날짜: 2026-11-19
- 결정자: sehoone
- 관련: [ADR-0021](0021-projects.md) (프로젝트 — 기본 스킬 집합 보유 · instructions 합성 지점 공유) · [ADR-0011](0011-chat-streaming-contract.md) (chat — 스킬 주입 후에도 동일 스트리밍) · [ADR-0020](0020-user-portal-frontend.md) (포털 — 스킬 UI·데이터 스코핑) · [ADR-0022](0022-connectors-mcp.md) (커넥터 — 컴포저 토글 짝)

## Context (맥락)

claude.ai 컴포저에는 **스킬(Skills)** 토글이 있다. 본 결정에서는 이를 **가벼운 재사용 지침 프리셋**으로 해석한다 — 정식 Anthropic agent-skills(`SKILL.md` + 리소스/코드, 모델 자동 호출, 코드 실행 샌드박스)는 인프라 부담이 커 범위 밖(후속)으로 둔다.

현재 재사용 지침은 `gpts.instructions`·`project.instructions`(ADR-0021)뿐으로, **메시지 단위로 켜고 끄거나 조합**할 수 없다. 스킬은 이 지침을 **합성 가능한 최소 단위**로 일반화한 것이다.

## Decision (결정)

### 1. 새 도메인 `domains/skill/` (수직 슬라이스)

**테이블 `llmonl.skill`** (uuid PK — 관례):

```
id TEXT PK · user_id BIGINT · name · description
body TEXT NOT NULL DEFAULT ''   -- 지침 본문(system prompt에 합성)
icon TEXT · color TEXT
created_at · updated_at
```

(`is_public`·공유는 후속.) **라우터 `/api/v1/skills`**(`ApiResponse[T]`): CRUD.

### 2. system prompt 합성 — 명시적 우선순위

메시지 전송 시 활성 스킬 `body`를 system prompt에 합성한다. 누적 순서(위→아래):

```
베이스 system  <  project.instructions(ADR-0021)  <  활성 스킬(선택 순)  <  (사용자 턴)
```

명시 순서로 충돌을 예측 가능하게 둔다. 합성 지점은 **ADR-0021의 project instructions 주입 지점과 동일**(`ChatService.stream_message`).

### 3. chat 연동

`stream_message(...)`가 `active_skill_ids`를 받아 skill 도메인에서 `body`를 로드해 system prompt에 prepend한다. 순수 텍스트 주입이라 **engine 추가 없음**(chat가 주입, 도메인은 CRUD+인가).

### 4. 프로젝트·컴포저 연동 — claude.ai 인터페이스 참고

- **컴포저**: Connectors 칩(ADR-0022) 옆에 **Skills 칩**을 둔다(claude.ai의 ✦ 스킬 참고). 멀티셀렉트 팝오버로 대화별 on/off.

```
스킬 팝오버 (컴포저 [✦ 스킬] 클릭 · claude.ai 참고):
┌────────────────────────────┐
│ 스킬 (지침 프리셋)          │
│ 🔍 검색…                    │
│ ☑ 정중한 비즈니스 톤        │
│ ☑ 코드 리뷰어               │
│ ☐ 요약 전문가               │
│ ☐ SQL 생성기                │
│ ──────────────────────────│
│ + 새 스킬 만들기            │
└────────────────────────────┘
```

- **프로젝트(ADR-0021)**: 프로젝트가 **기본 활성 스킬 집합**을 보유 → 해당 프로젝트 대화에 자동 적용(프로젝트 홈 우측 패널의 "활성 스킬·커넥터").

### 5. gpts/project instructions와의 관계

스킬은 합성 가능한 최소 단위다. `project.instructions`·`gpts.instructions`는 그대로 두되, 향후 "암묵 스킬"로 일반화할지 재검토(후속). 데이터는 `user_id` 소유권 스코핑(ADR-0020 §3).

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **지침 프리셋 스킬** (채택) | 가벼움·즉시 유용, engine 변경 없음, 프로젝트/커넥터와 조합 | 정식 agent-skills 대비 능력 제한(수용 — 범위 명시) |
| 정식 Anthropic agent-skills(SKILL.md+코드) | 강력(코드·리소스·자동 호출) | 코드 실행 샌드박스 인프라 필요 — 범위 과대. 후속 승격 |
| project/gpts instructions로만 | 신규 테이블 없음 | 메시지 단위 토글·재사용·조합 불가 |
| 프롬프트를 클라이언트에만 저장 | 백엔드 무변경 | 공유·서버측 합성·프로젝트 연동 불가 |

## Consequences (결과)

**긍정**
- 구현이 가볍고 즉시 유용 — 순수 지침 주입이라 engine 무변경.
- 프로젝트(ADR-0021)·커넥터(ADR-0022)와 조합해 claude.ai식 컴포저 UX 완성.
- 명시적 우선순위로 지침 충돌을 예측 가능.

**부정 / 리스크**
- 스킬 다중 활성 시 system prompt 비대 → 토큰·지연↑. 개수/길이 가드 필요.
- "스킬"이 정식 Anthropic agent-skills와 명칭 혼동 가능 — 범위를 UI·문서에 명시.
- 프리셋이 많아지면 관리·검색 UX 필요.

**후속 작업 / 미결**
- 스킬 공유(`is_public`)·팀 라이브러리.
- 정식 agent-skills(코드 실행) 승격 ADR — 샌드박스 인프라 전제.
- 스킬 ↔ project/gpts instructions 통합(중복 누적 시).
