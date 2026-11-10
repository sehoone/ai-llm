---
description: V2 도메인을 v3 수직 슬라이스로 이식 (ADR-0004·0005 준수)
argument-hint: <domain-name> (예: agent, workflow)
---

`$ARGUMENTS` 도메인을 orchestration-v3로 이식한다. 이식 대기 도메인은 주로 `agent`·`workflow`.
시작 전 관련 ADR을 반드시 확인하고(아래), 불명확하면 사용자에게 범위를 물어본다.

## 1. 사전 확인
- 관련 ADR 읽기: 도메인 경계·계약은 `docs/adr/`. `agent`는 ADR-0005(엔진 레이어), `workflow`는 워크플로 엔진 ADR(`docs/adr/0019-workflow-engine.md`) 확인.
- V2 원본 위치 확인: `../orchestration-v2/`의 해당 도메인 코드. 계약·동작을 파악하되 **구조는 v3 컨벤션으로 재작성**(그대로 복붙 금지).
- 이미 골격이 있는지 확인: `apps/api/src/domains/$ARGUMENTS/`(현재 `__init__.py`만 있을 수 있음).

## 2. 수직 슬라이스 구현 (`apps/api/src/domains/$ARGUMENTS/`)
HTTP 경계 + 관계형 영속화만 이 레이어에 둔다.
- `schema.py` — 요청/응답 Pydantic 모델. 응답은 `core/response.ApiResponse[T]`로 감싼다.
- `repository.py` — `llmonl` 스키마 대상 SQLAlchemy 쿼리. DDL 필요 시 `init.sql`에 테이블 추가.
- `service.py` — 유스케이스 오케스트레이션. **AI 연산은 직접 하지 말고 `engine/`에 위임**.
- `api.py` — FastAPI 라우터. 인증은 `dependencies.get_current_user`(+ 필요 시 `require_admin`/`require_superadmin`).

## 3. AI 연산은 엔진으로 (ADR-0005)
- LLM·그래프·검색 등은 `apps/api/src/engine/`의 해당 모듈에 둔다. `engine`은 `domains`·FastAPI를 **import 금지**(단방향 `domains→engine→core`).
- 모델 조립은 per-request `LlmConfig` + `engine/llm.build_chat_model`(ADR-0010). DB 좌표는 도메인이 주입.
- 관측이 필요하면 도메인이 컨텍스트 값을 주입하고 계측은 `engine/observability`(ADR-0007).

## 4. 등록·계약
- `apps/api/src/main.py`에 라우터 등록(`/api/v1/$ARGUMENTS`). 공개 링크 등 미인증 경로가 있으면 별도 public router.
- 계약이 바뀌면 `task gen-types`로 web TS 재생성(단방향). web `src/api/*.ts`가 V2 기준이면 `/api/v1/*`·`ApiResponse`로 재매핑.

## 5. 검증
- `cd apps/api && uv run poe lint`(ruff + `lint-imports` 레이어 경계) + `uv run poe test`.
- 가능하면 `tests/domains/`·`tests/engine/`에 핵심 로직 테스트 추가.
- 마지막에 `convention-checker` 서브에이전트로 ADR-0005 경계·수직 슬라이스·ApiResponse·`llmonl`·인증 "검증만" 위반 점검.

> uv/ruff가 셸 PATH에 없으면 lint/test는 사용자에게 직접 실행을 요청한다.
