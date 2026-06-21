# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This monorepo contains three services that form an MCP API key management platform:

| Directory | Role | Stack |
|-----------|------|-------|
| `admin-front/` | Admin web UI | Next.js 16, React 19, TypeScript, pnpm |
| `platform-server/` | Auth + user management + API key issuance | Spring Boot 3.4, Java 21, Gradle |
| `spring-ai-mcp/` | MCP (Model Context Protocol) server | Spring AI 1.1.7, Spring Boot 3.4, Java 21 |

Each sub-module has its own `CLAUDE.md` with detailed commands and architecture. Read the relevant one before editing that service.

## How the Services Fit Together

```
Browser / MCP Client
  └──HTTP :80──► nginx (reverse proxy)
                  ├── GET /api/health  → admin-front (:3000)   ← exact match
                  ├── /api/*           → platform-server (:8080)
                  ├── /swagger-ui/*    → platform-server (:8080)
                  └── /mcp             → spring-ai-mcp (:8080)  ← SSE buffering off, timeout 1h

            platform-server (:8080)
            (auth · users · API key CRUD · JWT issuance)
                  │
                  │  POST /api/v1/api-keys/validate  (public endpoint, no JWT)
                  ▼
            spring-ai-mcp (:8080 internal / :8081 external)
            (validates Bearer sk-... against platform-server; 5-min cache)
```

- **nginx** is the single entry point on port 80.
- **platform-server** is the sole JWT issuer for admin-front and the API key store.
- **spring-ai-mcp** validates `Authorization: Bearer sk-...` by calling platform-server's `/api/v1/api-keys/validate`. Results are cached 5 min in a `ConcurrentHashMap`. No JWT secret is shared.
- **admin-front** embeds `NEXT_PUBLIC_API_URL` at build time (client-side axios). `API_URL` is read at runtime (server-side Next.js rewrite). Through nginx both resolve to `http://SERVER_IP` — no port suffix.

## Commands

### Full stack (Docker Compose)

```bash
cd deploy
cp .env.example .env          # set DB_PASSWORD, JWT_SECRET_KEY, NEXT_PUBLIC_API_URL

# Linux/macOS — deploy.sh writes NEXT_PUBLIC_API_URL to admin-front/.env.production first
./deploy.sh up -d --build

# Windows PowerShell
Set-Content ../admin-front/.env.production "NEXT_PUBLIC_API_URL=http://192.168.1.100"
docker compose up -d --build
```

> **NEXT_PUBLIC_API_URL gotcha**: this var is baked into the JS bundle at build time. Never set it to `localhost` for a server deployment — the browser runs on the client machine, not the server. Also exclude `.env.local` from `.dockerignore` so it cannot override `.env.production` inside the image.

Verify all five containers are healthy:
```bash
docker compose ps
curl -o /dev/null -w "%{http_code}" http://localhost/api/health   # 200
```

### Local development (service-by-service)

Start in order (each depends on the previous):

```bash
# 1. PostgreSQL only
cd deploy && docker compose up -d db

# 2. platform-server (PowerShell)
cd platform-server
$env:APP_ENV='local'; $env:JWT_SECRET_KEY='your-32-char-secret-here!!'
$env:POSTGRES_HOST='localhost'; $env:POSTGRES_PORT='5432'
$env:POSTGRES_DB='llm_db'; $env:POSTGRES_USER='postgres'; $env:POSTGRES_PASSWORD='postgres'
./gradlew bootRun
# Swagger: http://localhost:8080/swagger-ui/index.html

# 3. spring-ai-mcp (PowerShell) — port conflict: change server.port to 8081 if platform-server already uses 8080
$env:SPRING_PROFILES_ACTIVE='local'; ./gradlew bootRun

# 4. admin-front
cd admin-front && pnpm dev    # http://localhost:3000
```

### platform-server

```powershell
./gradlew compileJava
./gradlew test                                                 # H2 in-memory (application-test.yml)
./gradlew test --tests "com.sehoon.platform.auth.AuthServiceTest"
./gradlew bootJar
```

### spring-ai-mcp

```powershell
./gradlew build -x test
./gradlew test     # Testcontainers (Docker must be running; auto-skipped if Docker is absent)
./gradlew test --tests "com.example.mcpserver.McpServerApplicationTests"
./gradlew bootJar
```

> **Windows Testcontainers**: Docker Desktop 29.x uses `npipe:////./pipe/docker_cli`. `build.gradle` injects this automatically; tests skip if Docker Desktop is not running (`failOnNoDiscoveredTests = false`).

### admin-front

```bash
pnpm dev
pnpm build && pnpm start
pnpm lint
pnpm format
pnpm knip          # dead code analysis
```

## Initial Setup Workflow

After the first `docker compose up`:

```bash
# 1. Register first account (created as USER role)
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"Admin1234!"}'

# 2. Promote to ADMIN via DB
docker compose exec db psql -U postgres -d llm_db \
  -c "UPDATE llmonl.users SET role='ADMIN' WHERE email='admin@example.com';"

# 3. Issue a MCP API key
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin1234!"}' \
  | grep -o '"accessToken":"[^"]*"' | cut -d'"' -f4)

curl -X POST http://localhost/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-mcp-client"}'
# response.key contains the full sk-... value — shown only once
```

## Key Cross-Cutting Decisions

- **Database split**: platform-server owns `llm_db` PostgreSQL → `llmonl` schema (`users`, `api_key`, `refresh_token`). spring-ai-mcp uses `sample_db` → `sample_item` table. Both DBs share one PostgreSQL instance. Schema created by `deploy/initdb/init.sh` on first container startup.
- **ddl-auto**: `validate` in all non-test profiles. Tables must exist before startup. `test` profile uses H2 with `create-drop`.
- **UserRole**: `SUPERADMIN` | `ADMIN` | `USER` only. (MANAGER, CASHIER were removed.)
- **API key format**: `sk-` prefix, 32 bytes random. Full key returned only once at creation time; subsequent GETs return a masked value.
- **JWT HS256**: `JWT_SECRET_KEY` env var required in platform-server. No JWT is shared with spring-ai-mcp — MCP auth uses API keys only.
- **MCP transport**: Streamable HTTP at `POST /mcp`. To switch to stdio, swap `spring-ai-starter-mcp-server-webmvc` → `spring-ai-starter-mcp-server-stdio` and add `spring.main.web-application-type: none`.
- **Adding a new MCP Tool**: annotate the class with `@Component` and `@Tool`, then add it to **both** the `mcpToolCallbackProvider()` parameter list **and** the `toolObjects()` call in `McpConfig.java`. Prompts and Resources only need `@Bean`.
- **spring-ai-mcp filter chain order**: `ForwardedHeaderFilter` → `MdcLoggingFilter` (+1) → `RateLimitFilter` (+2, 60 req/min/IP → 429) → `ApiKeyAuthFilter` (validates key, sets SecurityContext).
- **Platform-server common response**: all endpoints return `ApiResponse<T>` — `{success, message, data}` via static factories `ok(data)` / `fail(message)`. Domain exceptions use `BusinessException(ErrorCode)` → `GlobalExceptionHandler`.
- **admin-front import order** (enforced by Prettier plugin): `react` → third-party → `@/api` → `@/stores` → `@/lib` → `@/utils` → `@/constants` → `@/context` → `@/hooks` → `@/components` → `@/features` → relative.
- **Logging**: use `import { logger } from '@/lib/logger'` in admin-front (pino, debug in dev / warn+ in prod). In spring-ai-mcp, `LoggingAspect` AOP auto-logs `@Tool` START/END/ERROR (argument count only, no values).

## Monitoring Stack

Run after the app stack is up (shares `mcp-platform-net`):

```bash
cd deploy/monitor
cp .env.example .env   # set GRAFANA_PASSWORD
docker compose up -d
# Grafana: http://localhost:3001  |  Prometheus: http://localhost:9090
```

Prometheus scrapes platform (`platform:8081/actuator/prometheus`) and mcp (`mcp:8081/actuator/prometheus`) every 15 s. Grafana dashboards and alert rules are auto-provisioned. Import Spring Boot JVM dashboard via ID `19004`.

## MCP Client Connection

```bash
# MCP Inspector (test)
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP | URL: http://YOUR_SERVER_IP/mcp
# Header: Authorization: Bearer sk-your-api-key
```

`claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mcp-platform": {
      "url": "http://YOUR_SERVER_IP/mcp",
      "headers": { "Authorization": "Bearer sk-your-api-key" }
    }
  }
}
```
