# ADR-0003: 단일 Python 백엔드 + 사내 IdP 인증 위임

- 상태: Accepted
- 날짜: 2026-10-17
- 결정자: sehoon
- 관련: [ADR-0001](0001-monorepo-structure.md) (개정), [ADR-0002](0002-polyglot-and-auth-boundary.md) (대체)

## Context (맥락)

V3 상용 설계를 진행하며 ADR-0002가 채택한 **폴리글랏(Python+Java+TS)** 의 비용을 재평가했다.
핵심 우려는 **"계약 중복과 drift"** 였다:

- JWT payload·API DTO 같은 서비스 간 계약이 Java·Python·TS에 **각각 복제**된다(언어가 달라 코드 공유 불가).
- 한쪽만 바뀌고 나머지가 뒤처지면(drift) **컴파일·단위 테스트는 통과**하고 **운영에서야 터지는** 숨은 버그가 된다.
- 이를 막으려면 `packages/contracts` codegen 파이프라인을 세 언어로 유지해야 하며, 상용 운영 부담이 크다.

이 비용을 줄이기 위해 **단일 언어로 단순화**하기로 했다. 웹 프론트엔드는 브라우저 특성상 TypeScript가
불가피하므로, 실제 결정 지점은 **"백엔드를 한 언어로"** 였고 후보는 두 가지였다:

1. **Java/Spring Boot + Spring AI** — 사내 표준·SSO와 정렬 우수.
2. **Python/FastAPI** — LLM 생태계(LangChain/LangGraph/Whisper 등) 유지.

평가 결과 **LLM 자산 유지가 결정적**이었다. Spring AI는 채팅·RAG·tool calling은 지원하나,
V2가 쓰는 **LangGraph 기반 상태형 워크플로/복잡 에이전트 오케스트레이션에 대응물이 없어** 자작 부담이 크다.
따라서 Python을 단일 백엔드 언어로 택한다.

Python 선택 시 남는 두 걸림돌과 해소:

- **사내 Java 표준과의 misalignment** — 기술이 아닌 조직 결정. 사내 합의를 전제로 수용한다.
- **SSO/SAML/LDAP** — Spring Security가 강점이던 영역. FastAPI에 직접 구현하면 보안 코드 자작 리스크가
  크다. → **사내 기존 IdP(OIDC)에 위임**하여 해소한다. 인증을 앱에서 꺼내 IdP로 옮기면
  "Spring Security가 필요해서 Java" 라는 제약 자체가 사라진다.

## Decision (결정)

### 1. 단일 Python 백엔드 + TS 프론트 (3서비스 → 2서비스)

- **backend** = FastAPI 단일. ADR-0002의 `platform-server`(Java) 책임(auth·user·api-key·llm-resource)을 Python으로 포팅하고, 기존 orchestrator의 LLM 도메인(chat·rag·agent·workflow·meeting)과 한 백엔드로 통합.
- **frontend** = Next.js(TS), admin-front 계승.

### 2. 인증은 사내 기존 IdP에 위임

- 로그인·SSO·SAML·LDAP 페더레이션은 **사내 IdP가 전담**.
- FastAPI는 IdP의 **JWKS로 OIDC 토큰 서명·클레임을 검증만** 한다. 인증 로직 자작 없음.
- 토큰 발급·세션은 앱이 소유하지 않는다.

### 3. drift 제거 — 백엔드가 하나

- 백엔드끼리의 계약(JWT·DTO 복제)이 **원천적으로 사라진다**.
- 남는 계약은 **백엔드 OpenAPI → 프론트 TS 타입** 단방향 하나뿐. FastAPI가 `/openapi.json`을 자동 생성하므로 교차언어 codegen 파이프라인이 불필요하다.
- 백엔드 내부 공유는 언어가 같으므로 **그냥 import** (codegen 없이).

### 4. 툴링 단순화 — moon 철회

- 프로젝트가 사실상 2개(backend/frontend)라 moon의 폴리글랏 조율 가치가 사라진다.
- **얇은 `Taskfile.yml`**(`dev`/`lint`/`test`/`gen-types`) + **GitHub Actions `paths` 필터 CI**로 대체한다.
- backend: `uv`+`ruff`+`pytest`. frontend: `pnpm`+`eslint`.

### 5. 디렉토리 구조

> ⚠️ 이 섹션의 최상위 네이밍(`backend/`·`frontend/`·`contracts/`)은 [ADR-0004](0004-apps-packages-monorepo-layout.md)에서
> `apps/api`·`apps/web`·`packages/contracts`로 개정됨. 아래는 결정 당시 기록으로 보존.

```
orchestration-v3/
├─ backend/                 # FastAPI (uv) — domains/{chat,rag,agent,workflow,meeting,
│  │                        #   user,api_key,llm_resource,auth} + core/
├─ frontend/                # Next.js (FSD: app/features/entities/shared)
├─ contracts/openapi.json   # FastAPI export → 프론트 TS 타입 (단방향)
├─ deploy/                  # V2 계승 (keycloak 불필요 — 사내 IdP 사용)
├─ tools/  docs/adr/  Taskfile.yml  README.md  CLAUDE.md
```

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **폴리글랏 유지 (ADR-0002)** | 각 언어 강점, 사내 Java 표준·SSO 정렬 | 계약 중복·drift의 상용 운영 부담. 본 ADR로 대체. |
| **Java/Spring + Spring AI 단일** | 사내 표준·SSO와 최상 정렬 | LangGraph류 상태형 워크플로/복잡 에이전트 대응물 없어 LLM 자작 부담 큼. |
| **FastAPI에 SSO/SAML/LDAP 직접 구현** (python3-saml·Authlib·ldap3) | 외부 의존 없음 | 보안 민감 코드 자작 리스크. 사내 IdP 위임으로 대체. |
| **Keycloak 신규 도입** | off-the-shelf IdP | 사내 기존 IdP가 있으므로 불필요. |

## Consequences (결과)

**긍정**
- **drift 소멸** — 백엔드 단일화로 교차언어 계약 복제가 사라짐. 남는 계약은 단방향 1개.
- **인증 자작 없음** — SSO/SAML/LDAP를 사내 IdP에 위임, FastAPI는 검증만.
- **Python LLM 자산 유지** — LangGraph·Whisper 등 그대로.
- **툴링 단순화** — moon·교차언어 codegen 파이프라인 제거, 얇은 Taskfile로 충분.

**부정 / 리스크**
- `platform-server`(Java)의 auth·user·api-key·llm-resource를 **Python으로 포팅**하는 작업량(전형적 CRUD라 난도는 낮음).
- **사내 Java 표준과의 misalignment** — 조직 합의가 전제. 미확보 시 재검토.
- **사내 IdP에 대한 런타임 의존** — IdP 가용성·OIDC 연동 설정(JWKS 엔드포인트, 클레임 매핑, 역할 매핑)이 선결 과제.

**후속 작업**
- ADR-0001을 Superseded 처리(완료), moon→Taskfile 전환 반영.
- OIDC 토큰 검증 설계(JWKS 캐싱, role 클레임 매핑, 토큰 만료·갱신 흐름).
- platform 도메인(auth·user·api-key·llm-resource) Python 포팅 계획 수립.
- V3 골격 스캐폴딩(backend/·frontend/·deploy/·Taskfile.yml).
