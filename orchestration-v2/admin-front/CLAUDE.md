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
docker build --build-arg ENV_FILE=.env -t llm-admin .
```

There is no test suite configured.

## Environment Variables

Copy `.env.example` to `.env`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000  # Client-side axios base URL; falls back to /api
API_URL=http://localhost:8000              # Server-side rewrite destination
NEXT_PUBLIC_WS_URL=                       # WebSocket URL for evaluation feature (optional; auto-derived from NEXT_PUBLIC_API_URL if unset)
```

`next.config.mjs` rewrites all `/api/*` requests to `${API_URL}/api/*`. Client-side axios uses `NEXT_PUBLIC_API_URL` directly (falls back to `/api`). The distinction matters: `API_URL` is never sent to the browser; `NEXT_PUBLIC_*` vars are embedded at build time.

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

### Feature Structure

Each feature lives in `src/features/<feature-name>/` with an `index.tsx` entry point. The corresponding page in `src/app/(authenticated)/` simply imports and renders it.

Active features:
- `chats/` — LLM chat with session management and streaming responses
- `gpts/` — Custom GPT CRUD; create/edit/delete/chat with custom GPTs
- `agents/` — Configurable AI agents with RAG integration (`rag_keys`, `rag_groups`), tool selection, session management, streaming chat; supports `model_override` and `is_deep_thinking`
- `workflows/` — Visual workflow builder (`@xyflow/react` v12) with node-based execution, SSE streaming, cron schedules, webhooks, and dynamic API endpoints
- `chat-history/` — Read-only admin view of all users' chat history
- `rag-documents/` — Upload and manage documents for RAG knowledge base; includes groups/keys tab for organizing document namespaces
- `natural-search/` — Natural language search over data sources
- `evaluation/` — AI voice interview evaluation (Korean-language UI); uses WebSocket + Azure Speech SDK for STT/TTS
- `llm-resources/` — Configure LLM provider endpoints (failover/fallback)
- `api-keys/` — Manage authentication keys
- `users/` — User management table with CRUD
- `dashboard/` — Analytics overview

Inactive (routes exist, sidebar entries commented out): `tasks/`, `apps/` — starter scaffolding not wired to backend.

### API Layer

All backend calls live in `src/api/`. Each file exports typed functions using the shared Axios instance from `src/api/axios.ts`. Available LLM models are enumerated in `src/config/models.ts` (`LLM_MODELS`, `DEFAULT_LLM_MODEL`).

**SSE streaming pattern** (used by chat, agents, and workflows):
```typescript
api.post(endpoint, data, {
  onDownloadProgress: (progressEvent) => {
    const xhr = progressEvent.event?.target as XMLHttpRequest
    const newText = xhr.responseText.slice(lastPosition)
    lastPosition = xhr.responseText.length
    // split on '\n\n', parse 'data: {json}' lines
    // handle [DONE] sentinel and feature-specific event types
  }
})
```

Streaming event types by feature:
- **Chat/Agents**: `{ content: string, done: boolean }` | `{ type: 'title', title: string }`
- **Workflows**: `{ type: 'node_start' | 'node_complete' | 'node_failed' | 'execution_complete' | 'execution_failed', ... }`

Only `workflowApi.runStream()` exposes an `AbortController`-based cancel function.

Notable non-streaming APIs:
- `src/api/rag.ts` — Document upload and management
- `src/api/rag-groups.ts` — RAG group and key management (`ragGroupApi`)
- `src/api/custom-gpts.ts` — Custom GPT CRUD

### WebSocket (Evaluation Feature)

- `src/utils/websocket.ts` — `WebSocketClient` with auto-reconnect (5 attempts, exponential backoff); listener pattern (on/off/emit)
- `src/hooks/websocket/use-websocket.ts` — React hook exposing `sendText`, `sendAudio`, `evaluate`, `reset`
- WebSocket URL: uses `NEXT_PUBLIC_WS_URL` if set; otherwise derives from `NEXT_PUBLIC_API_URL` (http→ws protocol swap, appends `/ws/conversation`)
- Sent message types: `{ type: 'text' | 'audio' | 'reset' | 'evaluate', ... }`
- Azure Speech SDK (`microsoft-cognitiveservices-speech-sdk`) handles STT/TTS; hooks in `src/hooks/audio/`

### Global Providers (`src/app/providers.tsx`)

Wraps the app in: TanStack Query → DirectionProvider → FontProvider → ThemeProvider. Query client: retries disabled entirely in dev, disabled for 401/403 in prod (or after >3 failures); 10s stale time; `refetchOnWindowFocus` only in prod; mutation errors auto-toasted via `src/lib/handle-server-error.ts` (reads `error.response?.data.title`).

### Layout System

Sidebar state persisted in cookies (`sidebar_state`, `layout_collapsible`, `layout_variant`) and read server-side by the authenticated layout to set initial React state. Nav structure defined in `src/components/layout/data/sidebar-data.ts`.

### Logging

Use `import { logger } from '@/lib/logger'` everywhere. Backed by pino — `debug` level in dev with pino-pretty, `warn+` in production.

### UI Components

shadcn/ui components in `src/components/ui/` (excluded from ESLint). Shared layout primitives (`Header`, `Main`) in `src/components/layout/`. Tailwind CSS v4 with custom theme at `src/styles/theme.css`. Forms use React Hook Form + Zod v4. Tables use TanStack Table v8.

Reusable data-table primitives in `src/components/data-table/`: `column-header`, `faceted-filter`, `pagination`, `toolbar`, `view-options`, `bulk-actions`. Use these when building any new tabular feature.

### Context Providers

Context implementations live in `src/context/`: `ThemeContext`, `FontContext`, `DirectionContext`, `LayoutContext` (sidebar open/collapsed/variant state), `SearchContext` (command menu). They are wired into `src/app/providers.tsx` which also sets up TanStack Query.

### Hooks

- `src/hooks/use-dialog.ts` — manages open/close state + selected data item for dialogs
- `src/hooks/use-mobile.ts` — responsive breakpoint detection
- `src/hooks/use-table-url-state.ts` — syncs TanStack Table filter/sort/pagination to URL search params
- `src/hooks/websocket/` — WebSocket integration for evaluation feature
- `src/hooks/audio/` — Azure Speech SDK STT/TTS hooks for evaluation feature

### Code Quality

ESLint flat config ignores `src/components/ui/` and `.next/`. Key rules: no `console` (use logger), `_`-prefixed variables allowed as unused, inline `import type`. Prettier config in `.prettierrc` with Tailwind class sorting plugin.

**Import sort order** (enforced by `@trivago/prettier-plugin-sort-imports`):
```
react → third-party → @/api → @/stores → @/lib → @/utils → @/constants →
@/context → @/hooks → @/components → @/features → relative imports
```
