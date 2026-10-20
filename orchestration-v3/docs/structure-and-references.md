# 구조 근거와 참조 소스

orchestration-v3의 디렉터리 구조가 **왜 이렇게 생겼는지**와 그 결정을 뒷받침하는 **외부 표준·사실상 표준(de-facto standard) 소스**를 정리합니다.

- **결정(무엇을·왜 정했나)** 은 [`adr/`](adr/)에 있습니다. 이 문서는 그 결정이 업계 통용 관례와 어떻게 정렬되는지 **검증·근거**를 모읍니다.
- 검수 일자: 2026-10-21. 모든 외부 소스는 당시 원문을 직접 조회해 확인했습니다.

---

## 요약

| 영역 | v3 구조 | 뒷받침 표준 | 정렬 |
|------|---------|-------------|------|
| 모노레포 | `apps/*` + `packages/*` | Turborepo/Nx, Dify, n8n, uv workspace | ✅ |
| 백엔드 조립 | `APIRouter` + `include_router(prefix/tags)` | FastAPI 공식 문서 | ✅ |
| 백엔드 도메인 | `domains/<d>/` 수직 슬라이스 | fastapi-best-practices, Netflix Dispatch | ✅ |
| 백엔드 계층 | api→service→repository→model | SQLModel 3~4계층, Repository 패턴 | ✅ |
| 공통 코어 | `core/`(config·db·security·response) | full-stack-fastapi-template `app/core/` | ✅ |
| AI 격리 | `engine/`(FastAPI 비의존, import-linter 강제) | "서비스는 HTTP를 모른다" 원칙, Dify `core/` | ✅ (더 엄격) |
| 파일 네이밍 | 단수(`api·model·schema`) | 가이드는 복수(`router·models·schemas`) | ⚠️ 의도된 편차 |
| web | shadcn-admin 구조 + Next.js App Router | shadcn-admin | ✅ (Next 적응) |

---

## 1. 모노레포 레이아웃 — `apps/*` + `packages/*`

**근거 ADR**: [0004](adr/0004-apps-packages-monorepo-layout.md)

배포 단위는 `apps/*`, 서비스 간 공유물은 `packages/*`로 분리한다. 최상위 디렉터리가 역할(layer)이 아닌 **배포 단위**를 반영하도록 한다.

**참조 소스**
- [Turborepo / Nx 관례] — 배포 가능한 것은 `apps/*`, 공유물은 `packages/*` (업계 표준 모노레포 레이아웃).
- [Dify](https://github.com/langgenius/dify) — 백엔드 `api/`, 프론트 `web/` (역할이 아닌 산출물 이름).
- [n8n](https://github.com/n8n-io/n8n) — `packages/*` pnpm 모노레포.
- [How to Structure a Python Monorepo (acquaintsoft)](https://acquaintsoft.com/blog/python-monorepo-structure-growing-engineering-team) — `apps/`(배포 단위) vs `libs/`(임포트 전용) 분리. v3의 `packages/*`가 `libs` 역할.
- [uv workspace 공식 이슈 #10960](https://github.com/astral-sh/uv/issues/10960), [uv workspace how-to (pydevtools)](https://pydevtools.com/handbook/how-to/how-to-set-up-a-python-monorepo-with-uv-workspaces/) — 루트 `[tool.uv.workspace] members=["apps/*", ...]` + 단일 `uv.lock`.

**미결 / 후속**
현재 Python 앱은 `apps/api` 하나뿐이고 `packages/contracts`는 TS 생성물이라 **루트 uv 워크스페이스 선언은 불필요**하다. 두 번째 Python 앱(예: `apps/worker` — ADR-0005 §6의 engine 승격)이 생기면 그때 루트 워크스페이스 도입을 검토한다.

## 2. 백엔드 라우터 조립 — `include_router(prefix/tags)`

**근거**: [`apps/api/src/main.py`](../apps/api/src/main.py)

모듈별 `APIRouter`를 만들고 `main.py`에서 `include_router(prefix="/api/v1/...", tags=[...])`로 조립한다.

**참조 소스**
- [FastAPI 공식 — Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) — 바로 이 패턴(모듈별 `APIRouter`, `prefix`·`tags`·`dependencies` 주입, 공유 `dependencies.py`)을 공식 권장. v3 `main.py`·`auth/dependencies.py`와 일치.

> 공식 문서의 예시는 `routers/`(기술 타입) 레이아웃이지만 이는 **튜토리얼 규모** 기준이다. 대형 앱은 아래 도메인 기반이 정설이며 v3는 후자를 택했다.

## 3. 백엔드 도메인 — `domains/<d>/` 수직 슬라이스

**근거 ADR**: [0003](adr/0003-single-python-backend.md) · [`domains/README.md`](../apps/api/src/domains/README.md)

기술 타입(routers/·services/·models/)이 아니라 **비즈니스 도메인별**로 묶는다. 각 도메인이 자기 계층을 자체 보유한다.

**참조 소스**
- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) — 사실상 표준. `src/` 아래 도메인 패키지(`router·schemas·models·service·dependencies·constants·exceptions·utils`). 대형 모놀리식에 도메인 기반이 더 잘 확장된다고 명시.
- [Netflix Dispatch 영감 구조](https://deepwiki.com/proyecto-netflix/proyecto-netflix/4.1-fastapi-application) — 위 가이드의 원류. 기술 기능이 아닌 **비즈니스 능력(capability)** 기준 그룹핑.
- [How to Structure Your FastAPI Projects (Lavasani)](https://medium.com/@amirm.lavasani/how-to-structure-your-fastapi-projects-0219a6600a8f) — file-type vs feature/domain 비교, 대형은 도메인 기반 권장.

## 4. 백엔드 계층 — api → service → repository → model

**근거**: [`domains/user/`](../apps/api/src/domains/user/) 전 계층

HTTP(검증)는 `api.py`, 유스케이스는 `service.py`, 데이터 접근은 `repository.py`, SQLModel 정의는 `model.py`가 소유한다. 흐름: `HTTP → api → service → repository → DB`.

**참조 소스**
- [Scalable FastAPI + SQLModel: Three-Layer Architecture](https://medium.com/@faizulkhan56/building-a-scalable-fastapi-application-with-sqlmodel-a-complete-guide-to-three-layer-architecture-3c33ec981922) — API→Service→Repository→Model 계층. v3 슬라이스와 동일.
- [The Repository Pattern in FastAPI (DEV)](https://dev.to/alf_26/the-repository-pattern-in-fastapi-abstraction-or-overengineering-32ca) — Repository는 "ORM 완전 은닉"이 아닌 **앱 수준 데이터 접근 경계**로 쓰라. v3 `repository.py`가 SQLModel을 직접 다루는 방식과 부합.
- [FastAPI Architecture Best Practices (zyneto)](https://zyneto.com/blog/best-practices-in-fastapi-architecture) — "routes handle HTTP, services know nothing about HTTP, repositories own data access".

## 5. 공통 코어 — `core/`

**근거**: [`apps/api/src/core/`](../apps/api/src/core/)

도메인을 가로지르는 설정·DB·보안·응답 래퍼를 `core/`에 둔다.

**참조 소스**
- [full-stack-fastapi-template `app/core/`](https://github.com/fastapi/full-stack-fastapi-template/tree/master/backend/app/core) — 공식 템플릿의 `core/`에 `config.py`·`db.py`·`security.py`. v3 `core/`(+ `response.py`)와 일치.

## 6. AI 격리 — `engine/`

**근거 ADR**: [0005](adr/0005-ai-engine-layer.md) · [`engine/README.md`](../apps/api/src/engine/README.md)

AI 실행 능력(LLM·프롬프트·RAG·그래프·전사)을 HTTP 도메인에서 분리한다. `engine`은 `domains`·FastAPI를 **import하지 않으며**, `import-linter` 계약([`pyproject.toml`](../apps/api/pyproject.toml))이 `poe lint`에서 강제한다. 단방향: `domains → engine → core`.

**참조 소스**
- [FastAPI Architecture Best Practices (zyneto)](https://zyneto.com/blog/best-practices-in-fastapi-architecture) — "services know nothing about HTTP". v3는 이 원칙을 AI 레이어에 더 엄격히(정적 강제) 적용.
- [Dify `core/`](https://github.com/langgenius/dify) — agent·rag·workflow·model_runtime·prompt·tools를 HTTP API에서 분리(ADR-0005의 조사 근거).

## 7. 파일 네이밍 — 단수 (의도된 편차) ⚠️

v3는 `api.py`·`model.py`·`schema.py`(단수)를 쓴다. 통용 가이드는 `router.py`·`models.py`·`schemas.py`(복수)를 쓴다.

**이유**: 버그가 아니라 스타일 선택이며 **전 도메인이 일관되게 단수**를 따른다. 외부 기여자 혼선 방지를 위해 [`domains/README.md`](../apps/api/src/domains/README.md)에 이 컨벤션을 명시했다. (참조 가이드: fastapi-best-practices — 복수형)

## 8. web — shadcn-admin 구조

**근거 ADR**: [0006](adr/0006-web-structure-and-oidc.md)

**참조 소스**
- [shadcn-admin](https://github.com/satnaing/shadcn-admin) — `components·features·lib·stores·hooks·context·config·assets` 폴더. 원본은 **Vite + TanStack Router**라 `routes/`를 쓰지만, v3는 **Next.js App Router**라 `app/`으로 적응했다(나머지 폴더는 일치). FSD 아님.

---

## 검수 방법 메모

- **직접 원문 조회(WebFetch/WebSearch)**: FastAPI 공식 문서, fastapi-best-practices, full-stack-fastapi-template `core/`, shadcn-admin `src/` 트리·스택, uv workspace 문서.
- **저장소 파일 직접 Read**: `main.py`, `pyproject.toml`(import-linter 계약), `domains/user/*`, `auth/dependencies.py`, `core/*`, `domains·engine/README.md`, `Taskfile.yml`, `tools/export_openapi.py`.
- **결론**: v3 구조는 표준에 부합하며, 레이어 경계 강제·repository 레이어·engine 분리 면에서 오히려 통용 가이드보다 엄격하다. 실제 "틀린" 항목은 없고, 발견된 것은 모두 의도된 스타일(단수 네이밍)이거나 골격 단계의 자연스러운 미구현이다.
