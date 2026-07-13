# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pnpm dev              # 개발 서버 (:3000)
pnpm build            # 프로덕션 빌드 (standalone output)
pnpm start            # 프로덕션 서버 실행
pnpm lint             # ESLint
pnpm format           # Prettier
pnpm format:check     # 포맷 확인
pnpm exec tsc --noEmit  # 타입 체크 (테스트 없음)
pnpm knip             # 미사용 코드 분석
```

## Environment Variables

`.env.local` (로컬 개발용, 이미 설정됨):
```
NEXT_PUBLIC_API_URL=http://localhost:8080
```

Axios baseURL = `${NEXT_PUBLIC_API_URL}/api/` → `api.post('v1/embeddings')` = `POST http://localhost:8080/api/v1/embeddings`

`next.config.mjs`의 `/api/*` 리라이트는 SSR 전용. `NEXT_PUBLIC_*`는 빌드 시 번들에 포함 — Docker 빌드 전 `.env.production` 설정 필요.

## Architecture

**Next.js 16 App Router** · TypeScript strict · pnpm · `output: 'standalone'`

### Route Groups

- `src/app/(auth)/sign-in` — 공개 로그인 페이지
- `src/app/(authenticated)/` — 보호 영역. 서버 레이아웃에서 `access_token` 쿠키 검증 → 없으면 `/sign-in` 리다이렉트
- `src/app/(errors)/` — 401, 403, 500, 503 독립 에러 페이지

### Active Features

`src/features/<name>/index.tsx` → `src/app/(authenticated)/<name>/page.tsx` 1:1 대응

| Feature | Route | 설명 |
|---------|-------|------|
| `embeddings` | `/embeddings` | Tabs: 단건 입력 폼 / JSON 파일 일괄 업로드. 저장 문서 목록 + 삭제 |
| `search` | `/search` | 검색어 입력 → 코사인 유사도 결과 카드 (점수 바 포함) |

### API Layer (`src/api/`)

- `auth.ts` — login, refresh, logout
- `embeddings.ts` — createEmbedding, listEmbeddings, deleteEmbedding, **bulkUploadEmbeddings**, searchEmbeddings

공유 Axios 인스턴스(`axios.ts`) 사용. 인터셉터:
- 만료 2초 전 토큰 선제 갱신
- 갱신 중 요청 큐잉 (`failedQueue`)
- 401 시 1회 재시도 → 실패 시 `/sign-in` 리다이렉트

### 일괄 업로드 JSON 형식

```json
[{ "id": 1, "title": "제목", "desc": "내용" }, ...]
```

`id`는 참조용 식별자(DB 저장 안 됨), `desc`가 임베딩 텍스트로 사용됨.

### Global Providers (`src/app/providers.tsx`)

TanStack Query → DirectionProvider → FontProvider → ThemeProvider.  
Query client: dev에서 재시도 없음, 401/403 재시도 없음, stale time 10s, `refetchOnWindowFocus` prod only.

### Layout & Navigation

사이드바 상태는 쿠키에 저장되어 서버에서 읽힘. 메뉴 항목: `src/components/layout/data/sidebar-data.ts`.  
현재 메뉴: **임베딩 관리** (`/embeddings`) · **벡터 검색** (`/search`).

### Code Rules

- `console.*` 금지 → `import { logger } from '@/lib/logger'` (pino 기반)
- Zod numeric 필드: `z.coerce.number()` 금지 → `z.number()` (RHF 제네릭 타입 오류 방지)
- Zod v4에서 `ZodError.errors` → `ZodError.issues`
- `src/components/ui/` — ESLint 제외 (shadcn 생성)
- Import 정렬 (Prettier 강제): `react → 서드파티 → @/api → @/stores → @/lib → @/context → @/hooks → @/components → @/features → 상대경로`
