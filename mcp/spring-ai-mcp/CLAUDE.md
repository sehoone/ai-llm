# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 빌드 (테스트 제외)
./gradlew build -x test

# 실행 (Streamable HTTP, 포트 8080) — local 프로파일은 localhost PostgreSQL 사용
SPRING_PROFILES_ACTIVE=local ./gradlew bootRun

# JWT 시크릿키를 함께 설정할 경우
JWT_SECRET=<base64-secret> SPRING_PROFILES_ACTIVE=local ./gradlew bootRun

# JAR 빌드
./gradlew bootJar

# 테스트 — Testcontainers PostgreSQL (Docker 필요)
./gradlew test

# 단일 테스트
./gradlew test --tests "com.example.mcpserver.McpServerApplicationTests"
```

**Windows PowerShell:** 환경변수 인라인 설정 문법이 다르다.
```powershell
$env:JWT_SECRET="<base64-secret>"; $env:SPRING_PROFILES_ACTIVE="local"; ./gradlew bootRun
```

**로컬 실행 전제 조건:** `local` 프로파일은 `localhost:5432/sample_db`에 PostgreSQL이 필요하다. `deploy/dev`로 docker-compose를 쓰거나 직접 띄운 뒤 `deploy/initdb/init.sql`로 테이블을 초기화한다. `application-local.yml`에 로컬 개발용 JWT 시크릿키가 하드코딩되어 있으므로 로컬에서는 `JWT_SECRET` 환경변수가 없어도 기동된다.

**Windows Testcontainers:** Docker Desktop 29.x는 `docker_cli` named pipe를 사용한다. build.gradle이 자동으로 `npipe:////./pipe/docker_cli`를 주입하지만 Docker Desktop이 실행 중이지 않으면 테스트가 자동 skip된다 (`failOnNoDiscoveredTests = false`).

**테스트 프로파일:** `src/test/resources/application-test.yml`이 `ddl-auto: none`으로 덮어써서 Testcontainers로 뜬 빈 PostgreSQL에 DDL 검증 없이 컨텍스트 로드 테스트가 가능하다.

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

`SampleTool`은 `app.todo.base-url` 설정값이 필요하다 (`application-local.yml`에 기본값 `https://jsonplaceholder.typicode.com` 정의).

### DB 레이어

대상 테이블: `sample_item (id, name, description, price)`. DDL: `deploy/initdb/init.sql` (docker-compose는 PostgreSQL 최초 기동 시 자동 실행).

- **MyBatis**: `SampleItemMapper.java` + `src/main/resources/mapper/SampleItemMapper.xml`. 복잡한 쿼리·동적 SQL에 사용.
- **JPA**: `SampleItemRepository.java` (Spring Data). 단순 CRUD에 사용.

프로파일별 `ddl-auto`: `local`/`dev`/`stg` → `validate`, `prod` → `none`.

### 보안 — JWT 인증

외부에서 발급한 HMAC-SHA256 서명 JWT를 검증한다. `SecurityConfig`가 단일 `SecurityFilterChain`을 구성한다.

```
ForwardedHeaderFilter (HIGHEST_PRECEDENCE)
  → MdcLoggingFilter (+1): requestId·clientIp·clientName → MDC
  → RateLimitFilter (+2): IP당 60 req/min → 429
  → JwtAuthFilter: Authorization: Bearer <JWT> 서명 검증 → SecurityContext
```

#### JWT 형식

```json
{
  "sub": "agent-name",
  "roles": ["mcp-user"],
  "iat": 1749123456,
  "exp": 1749127056
}
```

- `sub`: SecurityContext의 principal (clientName)
- `roles`: `ROLE_MCP_USER` 등 권한으로 변환 (`-` → `_`, 대문자)
- 서명 알고리즘: HS256 (HMAC-SHA256)
- 토큰 발급은 MCP 서버 외부에서 수행. 서버는 검증만 한다.

#### 환경변수

| 변수 | 필수 | 설명 |
|---|---|---|
| `JWT_SECRET` | 필수 | HMAC-SHA256 서명 검증용 시크릿키 (Base64, 256비트 이상). `openssl rand -base64 32`로 생성. |

`local` 프로파일은 `application-local.yml`의 하드코딩된 개발용 키를 사용하므로 환경변수 불필요.

#### 구현 파일

| 파일 | 역할 |
|------|------|
| `global/security/jwt/JwtProperties.java` | `app.auth.jwt.secret` 바인딩 |
| `global/security/jwt/JwtAuthFilter.java` | Bearer 토큰 추출 → jjwt 검증 → SecurityContext 설정 |
| `global/security/SecurityConfig.java` | FilterChain 구성, public path 설정 |

### 로깅

`LoggingAspect`가 모든 `@Tool` 메서드의 START/END/ERROR를 AOP로 자동 기록한다 (파라미터 값은 PII 보호를 위해 인자 개수만 기록). 프로파일별 형식: `local`/`dev` → 텍스트 콘솔, `stg`/`prod` → Logstash JSON (MDC 필드 전체 포함).

### 포트 구성

| 포트 | 용도 |
|------|------|
| 8080 | MCP 엔드포인트 (`POST /mcp`), 앱 트래픽 |
| 8081 | Actuator (`/actuator/health`, `/actuator/prometheus`) — `dev`/`stg`/`prod` 프로파일 |

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
# Header: Authorization: Bearer <JWT>
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

`deploy/Dockerfile`이 빌드 이미지 정의. 환경별 docker-compose는 `deploy/{dev,stg,prod}/docker-compose.yml`에 위치하며 `context: ../..`(프로젝트 루트)로 빌드한다.

#### PostgreSQL 배포 모드

각 환경의 docker-compose는 `profiles: [db]`로 PostgreSQL을 선택적으로 포함한다.

```bash
# 내장 PostgreSQL 포함 기동 (개발/테스트용)
docker compose --profile db up -d --build

# 외부 PostgreSQL 사용 (운영 권장) — .env의 DB_URL을 외부 주소로 설정
docker compose up -d --build
```

상세 환경변수 목록 및 외부 DB 설정 방법은 `deploy/README.md` 참고.

#### 모니터링 스택

`deploy/monitor/`에 Prometheus + Grafana + Loki + Promtail compose가 별도로 있다. dev 또는 prod가 먼저 기동된 상태(Docker 네트워크 생성 필요)에서 실행한다.

```bash
cd deploy/monitor
cp .env.example .env   # APP_NETWORK=spring-ai-mcp-net (stg: spring-ai-mcp-stg-net)
docker compose up -d
```

접속: Grafana `http://localhost:3000`, Prometheus `http://localhost:9090`  
Spring Boot 대시보드: Dashboards → Import → ID `19004` → Datasource: Prometheus
