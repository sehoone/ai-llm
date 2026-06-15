# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pnpm dev          # Start development server (port 3000)
pnpm build        # Build for production (standalone output)
pnpm start        # Start production server
pnpm lint         # Run ESLint
pnpm format       # Format with Prettier
pnpm format:check # Check formatting
pnpm knip         # Dead code analysis
```

Docker build (pass `ENV_FILE=.env.production` for prod builds):
```bash
docker build --build-arg ENV_FILE=.env.production -t mcp-platform/admin .
```

There is no test suite configured.

## Environment Variables

Copy `.env.example` to `.env.local` for local dev:
```
NEXT_PUBLIC_API_URL=http://localhost:8080  # Client-side axios base URL; falls back to /api
API_URL=http://localhost:8080              # Server-side rewrite destination (runtime)
```

`next.config.mjs` rewrites all `/api/*` requests to `${API_URL}/api/*`. Client-side axios uses `NEXT_PUBLIC_API_URL` directly (falls back to `/api`). The distinction matters: `API_URL` is read at server-render time (standalone mode); `NEXT_PUBLIC_*` vars are embedded at build time.

> **Docker 배포 시**: `NEXT_PUBLIC_API_URL`은 빌드 시 번들에 포함됩니다. `.env.production` 에 브라우저가 접근하는 실제 서버 IP/도메인을 설정한 뒤 빌드해야 합니다.

## Architecture

**Next.js 16 App Router** with TypeScript (strict) and pnpm. Uses `output: 'standalone'` for Docker.

### Route Groups

- `src/app/(auth)/` — Public auth pages (sign-in, sign-up, forgot-password, otp)
- `src/app/(authenticated)/` — Protected pages; the layout server component checks for `access_token` cookie and redirects to `/sign-in` if absent
- `src/app/(errors)/` — Standalone error pages (401, 403, 500, 503)

### Authentication

- JWT tokens stored in cookies: `access_token`, `refresh_token`, `expires_at`
- Client state managed by Zustand in `src/stores/auth-store.ts` — initializes from cookies on load
- `src/api/axios.ts` — Axios instance with interceptors that:
  - **Proactively refresh** tokens 2s before expiry
  - **Queue** concurrent requests during an in-flight refresh (prevents race conditions via `failedQueue` array)
  - **Retry** on 401 after successful refresh; redirect to sign-in on refresh failure

### Active Features

Each feature lives in `src/features/<feature-name>/` with an `index.tsx` entry point. The corresponding page in `src/app/(authenticated)/` simply imports and renders it.

- `api-keys/` — MCP API 키 생성·조회·폐기; 생성 시 전체 키(`sk-...`)를 1회만 표시
- `users/` — User management table with CRUD (role, status)
- `dashboard/` — Static analytics overview (hardcoded demo data)
- `settings/` — Profile and account settings (profile, account sub-pages only)

### API Layer

All backend calls live in `src/api/`. Each file exports typed functions using the shared Axios instance from `src/api/axios.ts`.

- `src/api/auth.ts` — Login, refresh, logout
- `src/api/api-keys.ts` — API key CRUD
- `src/api/users.ts` — User list, get, update, delete

### Global Providers (`src/app/providers.tsx`)

Wraps the app in: TanStack Query → DirectionProvider → FontProvider → ThemeProvider. Query client: retries disabled entirely in dev, disabled for 401/403 in prod (or after >3 failures); 10s stale time; `refetchOnWindowFocus` only in prod; mutation errors auto-toasted via `src/lib/handle-server-error.ts` (reads `error.response?.data.title`).

### Layout System

Sidebar state persisted in cookies (`sidebar_state`, `layout_collapsible`, `layout_variant`) and read server-side by the authenticated layout to set initial React state. Nav structure defined in `src/components/layout/data/sidebar-data.ts`.

Sidebar nav groups: **General** (Dashboard, User Management) · **Configuration** (API Keys).

### Logging

Use `import { logger } from '@/lib/logger'` everywhere. Backed by pino — `debug` level in dev with pino-pretty, `warn+` in production.

### UI Components

shadcn/ui components in `src/components/ui/` (excluded from ESLint). Shared layout primitives (`Header`, `Main`) in `src/components/layout/`. Tailwind CSS v4 with custom theme at `src/styles/theme.css`. Forms use React Hook Form + Zod v4. Tables use TanStack Table v8.

Reusable data-table primitives in `src/components/data-table/`: `column-header`, `faceted-filter`, `pagination`, `toolbar`, `view-options`, `bulk-actions`. Use these when building any new tabular feature.

### Context Providers

Context implementations live in `src/context/`: `ThemeContext`, `FontContext`, `DirectionContext`, `LayoutContext` (sidebar open/collapsed/variant state), `SearchContext` (command menu). They are wired into `src/app/providers.tsx` which also sets up TanStack Query.

### Hooks

- `src/hooks/use-dialog-state.tsx` — manages open/close state + selected data item for dialogs
- `src/hooks/use-mobile.tsx` — responsive breakpoint detection
- `src/hooks/use-table-url-state.ts` — syncs TanStack Table filter/sort/pagination to URL search params

### Code Quality

ESLint flat config ignores `src/components/ui/` and `.next/`. Key rules: no `console` (use logger), `_`-prefixed variables allowed as unused, inline `import type`. Prettier config in `.prettierrc` with Tailwind class sorting plugin.

**Import sort order** (enforced by `@trivago/prettier-plugin-sort-imports`):
```
react → third-party → @/api → @/stores → @/lib → @/utils → @/constants →
@/context → @/hooks → @/components → @/features → relative imports
```
