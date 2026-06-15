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
                  ├── /            → admin-front (:3000)
                  ├── /api/*       → platform-server (:8080)
                  ├── /swagger-ui/ → platform-server (:8080)
                  └── /mcp         → spring-ai-mcp (:8080)

            platform-server (:8080)
            (auth · users · API key CRUD)
                  │
                  │  POST /api/v1/api-keys/validate
                  ▼
            spring-ai-mcp (:8080 internal / :8081 external)
            (MCP server — validates each request against platform-server)
```

- **nginx** is the single entry point on port 80. Routes by path prefix; MCP endpoint has SSE buffering disabled.
- **platform-server** is the single source of JWT issuance for the admin UI and the API key store for MCP clients.
- **spring-ai-mcp** authenticates requests via `Authorization: Bearer sk-...` — it calls platform-server's `/api/v1/api-keys/validate` and caches results for 5 minutes. No JWT secret is shared.
- **admin-front** embeds `NEXT_PUBLIC_API_URL` at build time (client-side axios) and reads `API_URL` at runtime (server-side Next.js rewrite proxy). With nginx, `NEXT_PUBLIC_API_URL` is just `http://SERVER_IP` — no port needed.

## Docker Compose Deployment

전체 스택을 단일 서버에 배포하려면 `deploy/` 디렉토리를 사용합니다. 자세한 내용은 [`deploy/README.md`](deploy/README.md) 참고.

```bash
cd deploy
cp .env.example .env   # DB_PASSWORD, JWT_SECRET_KEY, NEXT_PUBLIC_API_URL 필수 설정
./deploy.sh up -d --build
```

- `NEXT_PUBLIC_API_URL`은 Nginx 경유이므로 포트 없이 서버 IP/도메인만 입력합니다 (예: `http://192.168.1.100`).
- 최초 기동 시 `initdb/init.sh`가 자동으로 실행되어 `llm_db`(`llmonl` 스키마)와 `sample_db`를 생성합니다.

**Docker 서비스명 (`name: mcp-platform`):**

| 서비스 | 컨테이너 | 외부 포트 | 비고 |
|--------|---------|----------|------|
| `db` | mcp-platform-db | — | |
| `nginx` | mcp-platform-nginx | **80** | 단일 진입점 |
| `platform` | mcp-platform-platform | 8080 | 직접 접근용 |
| `mcp` | mcp-platform-mcp | 8081 | 직접 접근용 |
| `admin` | mcp-platform-admin | 3000 | 직접 접근용 |

## Running Locally

Start services in this order:

1. **PostgreSQL** — `cd deploy && docker compose up -d db` (또는 기존 PostgreSQL 사용)
2. **platform-server** — `APP_ENV=local ./gradlew bootRun` from `platform-server/`
3. **spring-ai-mcp** — `SPRING_PROFILES_ACTIVE=local ./gradlew bootRun` from `spring-ai-mcp/`. Requires platform-server to be running for API key validation.
4. **admin-front** — `pnpm dev` from `admin-front/`

**포트 충돌 주의:** platform-server와 spring-ai-mcp는 각각 기본 포트 8080을 사용합니다. 동시에 로컬 실행할 경우 spring-ai-mcp의 `server.port`를 `8081`로 변경하고 `application-local.yml`의 `platform-url`을 `http://localhost:8080`으로 유지하세요.

## Key Cross-Cutting Decisions

- **Nginx routing**: `deploy/nginx/nginx.conf`가 포트 80 단일 진입점을 처리. `/api/health`는 exact match로 admin-front로, `/api/*`는 platform-server로, `/mcp`는 spring-ai-mcp로 라우팅. MCP 경로는 SSE를 위해 `proxy_buffering off` + timeout 1h 적용.
- **API key authentication**: MCP 클라이언트는 `Authorization: Bearer sk-...` 헤더로 spring-ai-mcp에 요청 → spring-ai-mcp가 platform-server의 `/api/v1/api-keys/validate` (공개 엔드포인트)를 호출해 검증. 결과는 5분 인메모리 캐시(`ConcurrentHashMap`).
- **Database split**: platform-server는 `llm_db` PostgreSQL의 `llmonl` 스키마(`users`, `api_key`, `refresh_token`)를 소유. spring-ai-mcp는 `sample_db`의 `sample_item` 테이블만 사용. 두 DB는 같은 PostgreSQL 인스턴스에 공존.
- **UserRole**: `SUPERADMIN` | `ADMIN` | `USER` 세 가지만 존재 (MANAGER, CASHIER 제거됨).
- **MCP transport**: Streamable HTTP at `POST /mcp`. To switch to stdio, swap `spring-ai-starter-mcp-server-webmvc` → `spring-ai-starter-mcp-server-stdio` and add `spring.main.web-application-type: none`.
