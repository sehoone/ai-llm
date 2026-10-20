# ADR-0002: 폴리글랏 3서비스 유지와 인증 경계

- 상태: **Superseded by [ADR-0003](0003-single-python-backend.md)** (2026-10-17)
- 날짜: 2026-10-17
- 결정자: sehoon
- 관련: [ADR-0001](0001-monorepo-structure.md), [ADR-0003](0003-single-python-backend.md)

> ⚠️ **대체됨**: 폴리글랏(Python+Java+TS)의 "계약 중복·drift" 비용이 상용 운영 부담으로 판단되어,
> 백엔드를 **Python 단일(FastAPI)로 통합**하기로 결정했습니다(ADR-0003). 인증은 Spring Security
> 대신 **사내 기존 IdP(OIDC) 연동**으로 해소합니다. 아래 본문은 결정 당시 기록으로 보존합니다.

## Context (맥락)

상용 전환을 앞두고 "폴리글랏(Python+Java+TS)을 유지할지, 백엔드를 한 언어로 통합할지"를 재검토했다.

구조상 고정 축이 둘 있다:

- **프론트엔드 TypeScript** — 웹 UI라 불가피.
- **백엔드 Python(FastAPI)** — `orchestrator-server`의 책임(LLM 채팅, RAG, LangGraph 워크플로우,
  에이전트, STT/회의록)은 **LLM 생태계가 Python 우선**이라 사실상 Python이 강제된다
  (LangChain/LangGraph/pgvector/Whisper 모두 Python 1급).

따라서 통합한다면 방향은 "Python 쪽으로 모으기" 하나뿐이고, 유일한 결정 지점은
**Java `platform-server`(인증·사용자·API키·LLM리소스)를 Python으로 흡수할 것인가**였다.
platform-server의 책임은 전형적 auth + CRUD로, Java가 기술적으로 *필수*는 아니다.

결정을 가른 두 입력(사내 상황):

1. **사내 백엔드 기술 표준 = Java/Spring.**
2. **인증 요구 = SSO/SAML/LDAP 연동 필요.**

## Decision (결정)

**폴리글랏 3서비스를 유지한다.** `platform-server`(Spring Boot)를 그대로 둔다.
백엔드를 Python으로 통합하지 않는다.

근거:

- **사내 표준이 Java/Spring** → 운영·배포·채용 정렬이 기술 단순화보다 우선한다. 사내 상용 시스템에서 이 정렬은 거의 항상 우위.
- **SSO/SAML/LDAP** → Spring Security는 SAML2·OIDC·LDAP/AD 연동이 성숙·검증됨. FastAPI 생태계로 같은 요구를 충족하려면 상용 인증을 사실상 자작하게 되며, 인증은 자작을 피해야 하는 영역이다. 이 항목이 결정타.

### 인증 경계

- **`platform-server`(Spring Security)가 인증의 단일 소유자.** SSO/SAML/LDAP, 로그인, JWT 발급·갱신 전담.
- **`orchestrator-server`(Python)는 발급된 JWT 검증만** 수행(HS256 공유 시크릿, V2 방식 계승). 인증 로직 중복 없음.
- **`admin-front`는 platform-server로만 로그인.**
- `JWT_SECRET_KEY`는 두 백엔드에서 반드시 동일.

### 폴리글랏 비용을 구조로 흡수: `packages/contracts`

언어 교차라 코드 공유가 불가하므로 **계약을 SSOT로 두고 codegen으로 연결**한다(ADR-0001의 `packages/contracts`).

- `jwt-claims.schema.json` — JWT payload 계약을 1곳에 정의 → orchestrator(Python)·admin-front(TS)로 타입 생성.
- `openapi/platform.yaml`, `openapi/orchestrator.yaml` — 각 서비스 API 스펙 SSOT → TS/Python 클라이언트 타입 생성.
- DTO·클레임 drift를 **CI에서 차단**(생성물과 소스 불일치 시 실패).

> JWT payload 계약(서비스 간 공유):
> `{ sub, username, email, role(USER|ADMIN|SUPERADMIN|MANAGER|CASHIER), iat, exp, jti }` — role 값은 대문자.

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **Python+TS 2언어 통합** (platform-server를 FastAPI로 흡수) | 인지 부하↓, 공유 라이브러리로 JWT 실제 코드 공유, moon의 Java 한계 소멸, 툴체인 2개 | **사내 표준(Java/Spring)과 불일치**, **SSO/SAML/LDAP를 자작하게 됨**. 두 결정 입력 모두 유지 쪽. |
| **백엔드를 Java로 통합** (LLM도 JVM에서) | 단일 백엔드 언어 | LLM 생태계가 Python 우선 — 역행. 기각. |
| **Go 등 제3언어로 platform 재작성** | 성능·단순 배포 | 언어를 줄이는 게 아니라 늘림. 목표와 반대. |

## Consequences (결과)

**긍정**
- 사내 운영·배포·채용과 정렬. 상용 인증(SSO/SAML/LDAP)을 성숙한 Spring Security로 안전하게 처리.
- 각 언어의 강점 유지(AI=Python, 엔터프라이즈 인증=Java/Spring, UI=TS).
- 인증 경계가 단일 소유자로 명확 — 검증 로직 중복 제거.

**부정 / 리스크**
- 3개 툴체인·런타임 유지 비용 지속. `packages/contracts` codegen 파이프라인으로 계약 비용을 상쇄해야 함(필수 후속 작업).
- moon의 JVM proxy 한계(ADR-0001)를 그대로 안고 감.
- 언어 교차 로직은 코드 공유 불가 — 공유가 필요하면 반드시 계약/codegen 경로로 설계해야 함.

**후속 작업**
- `packages/contracts`에 `jwt-claims.schema.json`·OpenAPI 스펙 작성 및 codegen 태스크 정의.
- platform-server에 SSO/SAML/LDAP 연동 설계(별도 ADR 후보).
- orchestrator-server JWT 검증을 생성된 클레임 타입 기반으로 구현.
