# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 빌드 (테스트 제외)
./gradlew build -x test

# 실행 (Streamable HTTP, 포트 8080) — local 프로파일은 localhost PostgreSQL 사용
SPRING_PROFILES_ACTIVE=local ./gradlew bootRun

# JAR 빌드
./gradlew bootJar

# 테스트 — Testcontainers PostgreSQL (Docker 필요)
./gradlew test

# 단일 테스트
./gradlew test --tests "com.example.mcpserver.McpServerApplicationTests"
```

**로컬 실행 전제 조건:** `local` 프로파일은 `localhost:5432/sample_db`에 PostgreSQL이 필요하다. `deploy/dev`로 docker-compose를 쓰거나 직접 띄운 뒤 `deploy/initdb/init.sql`로 테이블을 초기화한다.

**Windows Testcontainers:** Docker Desktop 29.x는 `docker_cli` named pipe를 사용한다. build.gradle이 자동으로 `npipe:////./pipe/docker_cli`를 주입하지만 Docker Desktop이 실행 중이지 않으면 테스트가 자동 skip된다.

**테스트 프로파일:** `src/main/resources/application-test.yml`이 `spring.security.oauth2.resourceserver.jwt.jwk-set-uri`를 가짜 URL로 덮어써서 Keycloak 없이 컨텍스트 로드 테스트가 가능하다.

## Architecture

Spring AI 1.1.7 기반 MCP 서버 (Java 21, Spring Boot 3.4.5). Streamable HTTP transport로 `/mcp` 단일 엔드포인트를 노출하며, 도메인별 Tool 클래스를 `McpConfig`에서 `MethodToolCallbackProvider`로 일괄 등록하는 구조다.

### Transport 전환

현재 Streamable HTTP/WebMVC transport (`spring-ai-starter-mcp-server-webmvc`). stdio transport로 전환 시:
1. `build.gradle`: `spring-ai-starter-mcp-server-webmvc` → `spring-ai-starter-mcp-server-stdio`
2. `application.yml`에 `spring.main.web-application-type: none` 추가
3. `server.port` 설정 제거

### Tool 등록 패턴

**새 Tool 추가 시 `McpConfig.java`의 `mcpToolCallbackProvider()` 파라미터와 `toolObjects()` 목록 양쪽 모두에 추가해야 한다.** Prompt와 Resource는 `@Bean`으로 선언하면 Spring Boot 자동구성이 감지한다.

```java
// Tool — McpConfig에 명시적 등록 필요
@Bean
public ToolCallbackProvider mcpToolCallbackProvider(SampleTool t1, MyNewTool t2) {
    return MethodToolCallbackProvider.builder().toolObjects(t1, t2).build();
}

// Prompt — @Bean 선언만으로 자동 등록
@Bean
public List<McpServerFeatures.SyncPromptSpecification> myPrompts() { ... }

// Resource — @Bean 선언만으로 자동 등록
@Bean
public List<McpServerFeatures.SyncResourceSpecification> myResources() { ... }
```

### MCP 요소 샘플 위치

| 요소 | 파일 | 내용 |
|------|------|------|
| Tool | `sample/tool/SampleTool.java` | 6가지 패턴 (단순 반환/Record/다중 파라미터/외부 API/검증/InMemory CRUD) |
| Tool (DB) | `sample/tool/SampleDbTool.java` | MyBatis와 JPA 동일 기능 비교 |
| Prompt | `sample/prompt/SamplePrompt.java` | 고정 프롬프트 / 인수 기반 동적 프롬프트 |
| Resource | `sample/resource/SampleResource.java` | text/plain 리소스 / application/json 리소스 |

Tool에서 예외를 던지면 MCP 오류로 전달된다. 입력 검증 오류는 예외 대신 오류 문자열을 반환하는 패턴(`sampleValidateAge`)도 있다.

### DB 레이어

대상 테이블: `sample_item (id, name, description, price)`. DDL: `src/main/resources/sql/sample_schema.sql` (docker-compose는 `deploy/initdb/init.sql`로 PostgreSQL 최초 기동 시 자동 실행).

- **MyBatis**: `SampleItemMapper.java` + `src/main/resources/mapper/SampleItemMapper.xml`. 복잡한 쿼리·동적 SQL에 사용.
- **JPA**: `SampleItemRepository.java` (Spring Data). 단순 CRUD에 사용.

프로파일별 `ddl-auto`: `local`/`dev`/`stg` → `validate`, `prod` → `none`.

### 보안 — 인증 모드 (`AUTH_MODE`)

환경변수 `AUTH_MODE`로 인증 방식을 선택한다 (기본값: `keycloak`). `@ConditionalOnProperty`로 두 모드의 `SecurityFilterChain`이 상호 배타적으로 활성화된다.

| `AUTH_MODE` | 활성 클래스 | 토큰 발급 | 토큰 검증 |
|---|---|---|---|
| `keycloak` (기본) | `KeycloakSecurityConfig` | Keycloak Client Credentials | Keycloak JWKS |
| `local` | `local.LocalSecurityConfig` | `POST /auth/token` | HMAC-SHA256 (HS256) |

공통 필터 순서:
```
ForwardedHeaderFilter (HIGHEST_PRECEDENCE)
  → MdcLoggingFilter (+1): requestId·clientIp·JWT sub(clientId) → MDC
  → RateLimitFilter (+2): IP당 60 req/min → 429
  → BearerTokenAuthenticationFilter: JWT 서명 검증 → JwtAuthConverter
```

#### Keycloak 모드

```bash
# dev docker-compose 환경 — Keycloak 포트 9191
TOKEN=$(curl -s -X POST http://localhost:9191/realms/mcp/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=mcp-client&client_secret=dev-secret-change-me&grant_type=client_credentials" \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
```

- `KEYCLOAK_ISSUER_URI`: JWT `iss` 클레임 검증값 (기본: `http://localhost:9090/realms/mcp`)
- Docker 내부 URL 불일치 시 `SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_JWK_SET_URI`로 JWKS URI를 별도 지정 (이때 `issuer-uri`는 OIDC discovery 없이 문자열 비교만 수행)
- JWT 클레임: `realm_access.roles` + `resource_access.<client-id>.roles` → `ROLE_MCP_USER`

#### Local 모드

```bash
# 토큰 발급
curl -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"mcp-client","password":"my-password"}'
# → { "access_token": "...", "token_type": "Bearer", "expires_in": 3600 }
```

필수 환경변수:
- `LOCAL_JWT_SECRET`: 최소 32자 (미달 시 `@PostConstruct`에서 즉시 실패)
- `LOCAL_AUTH_PASSWORD`: `{noop}평문` (개발) 또는 `{bcrypt}$2a$10$...` (운영)

JWT 클레임: `{ "iss": "spring-ai-mcp-local", "sub": username, "roles": [...] }`

### 로깅

`LoggingAspect`가 모든 `@Tool` 메서드의 START/END/ERROR를 AOP로 자동 기록한다 (파라미터 값은 PII 보호를 위해 인자 개수만 기록). 프로파일별 형식: `local`/`dev` → 텍스트 콘솔, `stg`/`prod` → Logstash JSON (MDC 필드 전체 포함).

### 포트 구성

| 포트 | 용도 |
|------|------|
| 8080 | MCP 엔드포인트 (`POST /mcp`), 앱 트래픽 |
| 8081 | Actuator (`/actuator/health`, `/actuator/prometheus`) — `dev`/`stg`/`prod` 프로파일 |
| 9191 | Keycloak (dev docker-compose) |

### Streamable HTTP 엔드포인트

| 역할 | 메서드 | 경로 |
|------|--------|------|
| initialize / 모든 JSON-RPC 메시지 | `POST` | `/mcp` |
| 세션 종료 | `DELETE` | `/mcp` |

첫 번째 POST 응답 헤더에 `Mcp-Session-Id`가 포함되며, 이후 요청에 이 헤더를 전달한다. `Accept: application/json, text/event-stream` 헤더가 필요하다.

```bash
# MCP Inspector 사용
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP | URL: http://localhost:8080/mcp
# Header: Authorization: Bearer <token>
```

### Claude Desktop 연동 (stdio 모드)

`%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "spring-ai-mcp": {
      "command": "java",
      "args": ["-jar", "/absolute/path/to/spring-ai-mcp-1.0.0.jar"]
    }
  }
}
```

### 배포

`deploy/Dockerfile`이 빌드 이미지 정의. 환경별 docker-compose는 `deploy/{dev,stg,prod}/docker-compose.yml`에 위치하며 `context: ../..`(프로젝트 루트)로 빌드한다. dev 환경은 Keycloak 컨테이너를 포함한다. 상세 환경변수 목록은 `deploy/README.md` 참고.
