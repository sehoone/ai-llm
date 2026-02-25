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

Docker build:
```bash
docker build --build-arg ENV_FILE=.env -t llm-admin .
```

## Environment Variables

Copy `.env.example` to `.env`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000  # Used client-side and for WebSocket URL
API_URL=http://localhost:8000              # Used by Next.js rewrite proxy
```

`next.config.mjs` rewrites all `/api/*` requests to `${API_URL}/api/*`. Client-side axios uses `NEXT_PUBLIC_API_URL` directly (falls back to `/api`).

## Architecture

**Next.js 16 App Router** with TypeScript and pnpm. Uses `output: 'standalone'` for Docker.

### Route Groups

- `src/app/(auth)/` — Public auth pages (sign-in, sign-up, forgot-password, otp)
- `src/app/(authenticated)/` — Protected pages; the layout server component checks for `access_token` cookie and redirects to `/sign-in` if absent
- `src/app/(errors)/` — Standalone error pages (401, 403, 500, 503)

### Authentication

- JWT tokens stored in cookies: `access_token`, `refresh_token`, `expires_at`
- Client state managed by Zustand in `src/stores/auth-store.ts` — initializes from cookies on load
- `src/api/axios.ts` — Axios instance with interceptors that proactively refresh tokens before expiry and retry on 401; calls `/api/v1/auth/refresh`

### Feature Structure

Each feature lives in `src/features/<feature-name>/` with an `index.tsx` entry point. The corresponding page in `src/app/(authenticated)/` simply imports and renders it.

Active features:
- `chats/` — LLM chat with session management and streaming responses (`chatService.streamMessage` uses SSE)
- `gpts/` — Custom GPT CRUD; create/edit/delete/chat with custom GPTs
- `chat-history/` — Read-only view of historical conversations
- `rag-documents/` — Upload and manage documents for RAG knowledge base
- `natural-search/` — Natural language search over data sources
- `evaluation/` — AI voice interview evaluation (Korean-language); uses WebSocket + Azure Speech SDK for STT/TTS
- `llm-resources/` — Configure LLM provider endpoints (failover/fallback)
- `api-keys/` — Manage authentication keys
- `users/` — User management table with CRUD
- `dashboard/` — Analytics overview

### API Layer

All backend calls live in `src/api/`. Each file exports typed functions calling the shared Axios instance from `src/api/axios.ts`. Notable:
- `src/api/chat.ts` — `chatService.streamMessage()` handles streaming via `ReadableStream`
- `src/api/rag.ts` — Document upload and management
- `src/api/custom-gpts.ts` — Custom GPT CRUD

### WebSocket (Evaluation Feature)

- `src/utils/websocket.ts` — `WebSocketClient` class handles connection, reconnection, and message framing
- `src/hooks/websocket/useWebSocket.ts` — React hook wrapping the client; exposes `sendText`, `sendAudio`, `evaluate`, `reset`
- The evaluation page (`src/app/(authenticated)/evaluation/page.tsx`) coordinates STT (Azure `microsoft-cognitiveservices-speech-sdk`), audio playback, and WebSocket messaging
- WebSocket URL derived from `NEXT_PUBLIC_API_URL` (http→ws conversion)

### Global Providers (`src/app/providers.tsx`)

Wraps the app in: TanStack Query, DirectionProvider, FontProvider, ThemeProvider. Query client is configured with auto-retry (disabled in dev for 401/403), 10s stale time, and mutation error toast handling via `src/lib/handle-server-error.ts`.

### Layout System

Sidebar state (open/collapsed/variant) is persisted in cookies (`sidebar_state`, `layout_collapsible`, `layout_variant`) and read by the authenticated layout server component. The sidebar nav is configured in `src/components/layout/data/sidebar-data.ts`.

### Logging

Use `import { logger } from '@/lib/logger'` everywhere. Backed by pino — outputs `debug` level in dev, `warn+` in production. Server-side uses `pino-pretty` for colored output.

### UI Components

shadcn/ui components are in `src/components/ui/`. Shared layout primitives (`Header`, `Main`) are in `src/components/layout/`. Tailwind CSS v4 with a custom theme at `src/styles/theme.css`.
