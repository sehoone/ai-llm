# ADR-0023: 관리자/사용자 포털 분리 (admin web ↔ user portal)

- 상태: Accepted
- 날짜: 2026-11-15
- 결정자: sehoone
- 관련: [ADR-0004](0004-apps-packages-monorepo-layout.md) (apps/* 레이아웃) · [ADR-0003](0003-single-python-backend.md) (단일 백엔드) · [ADR-0020](0020-user-portal-frontend.md) (**본 결정의 구현** — 포털 프론트·데이터 스코핑·셀프가입) · [ADR-0009](0009-self-id-password-auth.md) (공유 JWT 인증)

## Context (맥락)

`apps/web` 단일 프론트가 **관리 기능**(users·api_keys·llm_resources·settings)과 **최종 사용자 기능**
(chat·gpts·ai_overview·meeting)을 함께 담고 있었다. 두 사용자층의 요구는 근본적으로 다르다:

- **UX·브랜딩**: 사용자는 "클로드급" 챗 중심의 단순·제품형 경험, 관리자는 밀도 높은 테이블·폼.
- **번들·성능**: 관리자용 무거운 코드가 사용자 번들에 섞이면 안 된다.
- **노출면(보안)**: 관리자 라우트·코드가 일반 사용자에게 내려가지 않아야 한다.

백엔드는 단일 Python 백엔드(ADR-0003)이고 역할 가드·JWT 인증·단방향 타입 생성물(`packages/contracts`)을
이미 갖췄다. 즉 바꿀 것은 **프론트 경계**이지 백엔드 아키텍처가 아니다.

## Decision (결정)

**프론트를 역할별 두 배포 단위로 분리한다. 백엔드·인증·계약은 공유한다.**

| 축 | 관리자 | 사용자 |
|----|--------|--------|
| 앱 | `apps/web` (shadcn-admin) | `apps/portal` (제품형 챗) |
| 경로 | `/admin` (Next basePath) | `/` (루트) |
| 대상 | ADMIN·SUPERADMIN | USER (셀프가입 가능) |

- **라우팅**: nginx 단일 진입점에서 `/`→portal · `/admin`→web · `/api/*`→api (경로 분리). 운영에서
  서브도메인(`app.`/`admin.`) 전환 여지를 남긴다.
- **공유**: 백엔드(`apps/api`)·인증(ID/PW→JWT, ADR-0009)·`packages/contracts` 타입은 두 앱이 공유.
- **경계 강제**: 관리 엔드포인트는 `require_admin`으로 가드하고, 사용자 노출 도메인은 `user_id`
  **데이터 스코핑**을 강제한다(세부는 ADR-0020). 권한 상승·IDOR 방지가 분리의 전제.
- **공유 UI**: shadcn 프리미티브·테마는 **복사로 시작**하고, 중복이 커지면 `packages/ui`로 추출(YAGNI).

> 본 ADR은 "분리"라는 상위 아키텍처 결정을 공식화한다. 포털 프론트 구현·데이터 스코핑 감사·셀프가입의
> 세부는 [ADR-0020](0020-user-portal-frontend.md), "클로드급" 챗 단계별 계획은
> [`../portal-roadmap.md`](../portal-roadmap.md)가 담는다.

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **별도 앱 분리** (채택) | 번들·테마·노출면 완전 분리, ADR-0004 정렬 | 앱 2개 운영·공유코드 관리(수용 가능) |
| 단일 web에 route-group `(user)`/`(admin)` | 코드 공유 쉬움 | 번들 미분리 — 관리자 코드가 사용자에 내려감, 노출면 리스크 |
| 백엔드도 분리(사용자 BFF) | 노출면 최소 | 단일 백엔드(ADR-0003) 역행 — 계약 중복·drift 재발 |
| 서브도메인 즉시 도입 | 경계 가장 깨끗 | 인증서·DNS·CORS 선작업 필요 — 경로 분리로 시작이 비용 효율적 |

## Consequences (결과)

**긍정**
- 사용자/관리자의 UX·번들·노출면이 앱 경계로 분리된다.
- 백엔드·인증·타입은 공유 유지 — ADR-0003·drift 제거 원칙 보존.
- nginx 단일 진입점·compose 패턴을 그대로 쓰므로 배포 변경이 작다.

**부정 / 리스크**
- **데이터 스코핑이 분리의 선결 전제** — 누락 시 IDOR. (감사·수정은 ADR-0020에서 완료.)
- 앱 2개 운영(빌드·배포·의존성) + 공유코드 중복 — 누적 시 `packages/ui` 추출.
- web `basePath=/admin` 도입으로 원시 절대경로(공개 공유 링크 등) 점검 필요 — ADR-0020 후속.
