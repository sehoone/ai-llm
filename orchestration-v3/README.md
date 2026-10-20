# orchestration-v3

LLM 오케스트레이션 플랫폼 v3. **단일 Python 백엔드(FastAPI) + Next.js 프론트엔드** 구성.
설계 결정은 [`docs/adr/`](docs/adr/) 참고 — 특히 [ADR-0003](docs/adr/0003-single-python-backend.md).

## 구조

```
orchestration-v3/
├─ apps/
│  ├─ api/       FastAPI 단일 백엔드 (uv) — LLM + 플랫폼 도메인, OIDC 토큰 검증
│  └─ web/       Next.js (TS) — 관리자 UI (admin-front 이식, shadcn-admin · OIDC — ADR-0006)
├─ packages/
│  └─ contracts/ api OpenAPI → web TS 타입 (단방향 생성물)
├─ deploy/       Docker Compose · Nginx · 관측 스택 (V2 계승 예정)
├─ tools/        OpenAPI export 등 유틸
├─ docs/adr/     아키텍처 결정 기록
└─ Taskfile.yml  루트 태스크 러너 (go-task)
```

## 핵심 설계 (ADR-0003)

- **백엔드 단일 언어(Python)** — 폴리글랏의 계약 중복·drift 비용 제거.
- **인증은 사내 기존 IdP(OIDC)에 위임** — FastAPI는 JWKS로 토큰 검증만. SSO/SAML/LDAP는 IdP 담당.
- **moon·교차언어 codegen 불필요** — 얇은 Taskfile + 단방향 OpenAPI→TS 생성.

## 개발

```bash
# 전제: uv, pnpm, go-task 설치
task dev          # api(:8000) + web(:3000) 동시 기동
task lint
task test
task gen-types    # api OpenAPI → web TS 타입 재생성
```

개별 서비스:
```bash
cd apps/api && uv sync --group dev && uv run poe dev   # :8000
cd apps/web && pnpm install && pnpm dev                # :3000
```

> ⚠️ 현재는 **골격(skeleton)** 단계입니다. 도메인 로직은 V2에서 이식 예정이며,
> 라우터·DB·OIDC 검증은 placeholder 상태입니다.
