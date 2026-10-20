# ADR-0001: 모노레포 구조와 태스크 오케스트레이션(moon)

- 상태: **Superseded by [ADR-0003](0003-single-python-backend.md)** (2026-10-17)
- 날짜: 2026-10-17
- 결정자: sehoon
- 관련: [ADR-0002](0002-polyglot-and-auth-boundary.md), [ADR-0003](0003-single-python-backend.md)

> ⚠️ **대체됨**: 단일 Python 백엔드로 전환(ADR-0003)하면서 폴리글랏 전제가 사라졌습니다.
> `apps/`+`packages/` 다프로젝트 전제와 **moon 태스크 오케스트레이션은 철회**되고, 프로젝트가
> `backend/`+`frontend/` 2개로 단순화되어 **얇은 Taskfile + paths 필터 CI**로 대체됩니다.
> "도메인 수직 슬라이스"·"CI 게이트 필수화" 같은 원칙은 ADR-0003에서도 유효합니다.
> 아래 본문은 결정 당시 기록으로 보존합니다.

## Context (맥락)

orchestration-v3은 orchestration-v2를 계승하되 **그린필드 전면 재아키텍처**로 시작한다.
현재 인력은 1인이지만 목표는 **사내 시스템에 적용하는 상용 서비스**이며, 곧 팀 확장과
프로덕션 SLA·보안·감사 요구를 전제한다.

V2는 한 git repo 안에 3개 서비스(`orchestrator-server`, `platform-server`, `admin-front`)와
`deploy/`가 평평하게 놓인 "느슨한 모노레포"였고, 다음이 부재했다:

- 루트 레벨 빌드/태스크 오케스트레이션 (각 서비스가 독립 섬)
- 서비스 간 공유 계약(contract)의 코드화 (JWT payload·DTO가 문서 규칙으로만 중복)
- CI (affected-only 빌드 없음, `.github/workflows` 자체가 없음)
- 통합 버전/릴리스 전략

스택은 **폴리글랏**이다: Python(FastAPI/uv) + Java(Spring Boot/Gradle) + TypeScript(Next.js/pnpm).
단일 언어 전용 툴(Turborepo=JS, Gradle 멀티모듈=JVM)로는 전체를 덮을 수 없다.

## Decision (결정)

### 1. 디렉토리 구조: `apps/` + `packages/` 분리

```
orchestration-v3/
├─ .moon/                    # 워크스페이스·툴체인·공통 태스크
├─ .github/workflows/        # ci.yml(moon ci), release.yml
├─ apps/                     # 배포 단위(deployable)
│  ├─ platform-server/       # Spring Boot
│  ├─ orchestrator-server/   # FastAPI
│  └─ admin-front/           # Next.js
├─ packages/                 # 공유물 (언어 교차는 codegen으로만 연결)
│  ├─ contracts/             # OpenAPI/JWT SSOT + 생성 타입  (→ ADR-0002)
│  ├─ ts/                    # TS 전용 공유 (api-client, ui, config 프리셋)
│  ├─ python/                # Python 전용 공유 (py-common)
│  └─ jvm/                   # JVM 전용 공유 (platform-common)
├─ deploy/                   # compose·k8s·nginx·observability (V2 계승)
├─ tools/                    # codegen·DB migration·운영 스크립트
└─ docs/                     # adr/, architecture.md
```

배포 단위(`apps/`)와 공유물(`packages/`)을 디렉토리로 명시적으로 분리한다. 모노레포 사실상 표준이며
"무엇을 배포하는가"가 한눈에 드러난다.

### 2. 태스크 오케스트레이션: moon

- `.moon/workspace.yml`이 모든 `moon.yml` 프로젝트를 등록해 의존 그래프를 구성한다.
- Python(uv)·Node(pnpm)는 moon 네이티브 toolchain으로 버전 고정.
- **Java는 moon 1급 toolchain이 아니므로 gradle을 호출하는 proxy 태스크**로 붙인다.
- `moon ci`가 affected(변경 영향) 그래프만 빌드/테스트하여 CI 시간을 단축한다.
- 공통 태스크(lint/format/test)는 `.moon/tasks/tag-*.yml`로 언어별 태그에 묶어 중복을 제거한다.

### 3. 서비스 내부: 도메인 수직 슬라이스 (재아키텍처의 실질)

- `platform-server`: `auth / user / apikey / llmresource` 도메인 패키지, 각 패키지 안에 web·service·domain·infra 계층(헥사고날 지향).
- `orchestrator-server`: `src/domains/{chatbot,rag,agent,workflow,meeting}` + `core/`(설정·DI·미들웨어·에러). V2의 평평한 `src/` 나열을 도메인 경계로 재편.
- `admin-front`: FSD(app/features/entities/shared) 스타일로 기능 응집.

### 4. CI는 PR 게이트로 필수화

`moon ci`가 affected 프로젝트만 lint/test/build. 통합 테스트·이미지 빌드·SBOM은 release 워크플로우로 분리.

## Alternatives considered (대안)

| 대안 | 장점 | 기각 사유 |
|------|------|-----------|
| **얇은 루트(Taskfile/Makefile) + GitHub Actions `paths` 필터** | 가장 단순, 추가 학습 거의 없음 | affected 감지·태스크 그래프·캐시를 수동 구성해야 함. 팀·프로덕션 확장 시 한계. |
| **Bazel / Pants** | 폴리글랏 단일 빌드 그래프, 재현성·원격 캐시 최상 | BUILD 파일 작성 부담·러닝커브 과도. 사내 표준이 이미 Bazel이 아닌 한 소규모엔 과투자. |
| **Nx** | 성숙한 모노레포 툴 | JS 중심. Python/JVM 폴리글랏 지원이 moon보다 약함. |
| **구조 유지(V2처럼 평평하게)** | 이동 비용 0 | 배포 단위/공유물 구분이 디렉토리로 안 드러남. 계약 중복 방치. |

## Consequences (결과)

**긍정**
- 배포 단위와 공유물이 구조로 명확. 신규 합류자가 repo를 빠르게 이해.
- affected-only CI로 빌드 시간 절약, 서비스 증가에도 확장.
- `packages/contracts` 자리를 확보해 서비스 간 계약 drift를 코드로 차단할 기반 마련(→ ADR-0002).

**부정 / 리스크**
- **moon의 JVM 지원이 proxy 수준**이라 platform-server 쪽은 moon 네이티브 이점(캐시 세분화 등)을 일부 못 누린다. JVM이 repo의 중심축이 되면 Gradle 멀티모듈 + moon 혼용을 재검토한다.
- 팀에 moon·모노레포 관례 학습 비용이 발생.
- 전면 재아키텍처는 가장 큰 이식 작업량을 요구(수용함 — 그린필드 결정).

**후속 작업**
- `.moon/workspace.yml`·`toolchain.yml` 및 각 `apps/*/moon.yml` 작성.
- `.github/workflows/ci.yml`(`moon ci`) 구성.
- ADR-0002의 `packages/contracts` codegen 파이프라인 정의.
