# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 빌드
./gradlew build

# 실행 (SSE transport, 포트 8080)
./gradlew bootRun

# JAR 빌드 (stdio transport 배포용)
./gradlew bootJar

# 테스트 (Docker 실행 필요 — Testcontainers PostgreSQL)
./gradlew test

# 단일 테스트 실행
./gradlew test --tests "com.example.mcpserver.McpServerApplicationTests"
```

## Architecture

Spring AI 1.1.7 기반 MCP 서버 (Java 21, Spring Boot 3.4.5). 도메인별 Tool 클래스를 `McpConfig`에서 `MethodToolCallbackProvider`로 일괄 등록하는 구조.

### Transport 전환

현재 SSE/WebMVC transport (`spring-ai-starter-mcp-server-webmvc`)로 실행 중. stdio transport로 전환 시:
1. `build.gradle`: `spring-ai-starter-mcp-server-webmvc` → `spring-ai-starter-mcp-server-stdio`
2. `application.yml`에 `spring.main.web-application-type: none` 추가
3. `server.port` 설정 제거

### Tool 등록 패턴

새 Tool 도메인 추가 시 `McpConfig.java`의 `mcpToolCallbackProvider()` 파라미터와 `toolObjects()` 목록 **양쪽 모두**에 추가해야 한다.

### MCP 세 가지 기본 요소 및 샘플 위치

| 요소 | 파일 | 설명 |
|------|------|------|
| Tool | `sample/tool/SampleTool.java` | 6가지 Tool 패턴 통합 |
| Tool (DB) | `sample/tool/SampleDbTool.java` | MyBatis / JPA 비교 패턴 |
| Prompt | `sample/prompt/SamplePrompt.java` | 고정 시스템 프롬프트 / 인수 기반 동적 프롬프트 |
| Resource | `sample/resource/SampleResource.java` | text/plain 리소스 / application/json 리소스 |

#### Tool 케이스별 패턴 (`SampleTool.java`)

| Case | 메서드 | 패턴 |
|------|--------|------|
| 1 | `sampleGreet` | 단순 문자열 반환 |
| 2 | `sampleGetProduct` | inner Record 반환 (MCP가 자동 JSON 직렬화) |
| 3 | `sampleCreateOrder` | 다중 파라미터 + `@ToolParam(description=...)` 명시 |
| 4 | `sampleGetTodo` | `RestClient` 외부 API 호출, timeout 설정, try-catch |
| 5 | `sampleValidateAge` | 입력값 검증 — 예외 대신 오류 문자열 반환 |
| 6 | `sampleAddMemo` / `sampleGetMemo` | 하나의 클래스에 복수 `@Tool` 메서드 + InMemory CRUD |

#### Prompt / Resource 등록 방식

Prompt와 Resource는 `@Configuration` 클래스에서 `@Bean`으로 등록한다. Spring Boot 자동구성이 아래 타입을 감지하여 MCP 서버에 자동 등록한다.

```java
// Prompt
@Bean
public List<McpServerFeatures.SyncPromptRegistration> myPrompts() { ... }

// Resource
@Bean
public List<McpServerFeatures.SyncResourceRegistration> myResources() { ... }
```

Tool은 `McpConfig`의 `MethodToolCallbackProvider`에 명시적으로 추가해야 한다 (`SampleTool` 참고).

### DB 레이어

대상 테이블: `sample_item (id, name, description, price)`. `SampleDbTool`이 MyBatis와 JPA 두 가지 접근법을 동일 기능으로 비교 제공한다.

- **MyBatis**: `SampleItemMapper.java` (인터페이스) + `src/main/resources/mapper/SampleItemMapper.xml` (SQL). 복잡한 쿼리·동적 SQL에 사용.
- **JPA**: `SampleItemRepository.java` (Spring Data). 단순 CRUD·타입 안전성에 사용.

### 보안

`app.security.api-key`가 기본값(`change-me-in-production`)이거나 비어 있으면 **앱 시작 시 즉시 실패**한다 (`SecurityConfig.validateApiKey()`). 환경변수 `API_KEY`로 전달하는 것이 표준이다.

필터 실행 순서 (`@Order` 기준):

```
ForwardedHeaderFilter (HIGHEST_PRECEDENCE)
  → MdcLoggingFilter (+1): requestId·uri·method·clientIp를 MDC에 설정
  → RateLimitFilter (+2): IP당 60 req/min 제한, 초과 시 429 반환
  → ApiKeyFilter: X-API-Key 헤더 검증
```

### 로깅

`LoggingAspect`가 모든 `@Tool` 메서드의 START/END/ERROR를 AOP로 자동 로깅한다. 파라미터 값은 PII 보호를 위해 로깅하지 않고 인자 개수(`args.count`)만 기록한다.

### 포트 구성

| 포트 | 용도 |
|------|------|
| 8080 | MCP 엔드포인트 (`POST /mcp`, Streamable HTTP), 앱 트래픽 |
| 8081 | Actuator (`/actuator/health`, `/actuator/prometheus`) — dev/prod 프로파일 |

### 테스트

`McpServerApplicationTests`는 Testcontainers로 PostgreSQL 컨테이너를 띄워 전체 컨텍스트를 검증한다. Docker가 없으면 자동으로 skip된다. Windows에서는 Docker Desktop의 named pipe(`npipe:////./pipe/dockerDesktopLinuxEngine`)를 사용하거나 `DOCKER_HOST` 환경변수를 설정한다.

### Streamable HTTP 엔드포인트 및 검증

transport는 **Streamable HTTP** 방식이며 단일 엔드포인트를 사용한다:

| 역할 | 메서드 | 경로 |
|------|--------|------|
| initialize / 모든 JSON-RPC 메시지 | `POST` | `/mcp` |
| 세션 종료 | `DELETE` | `/mcp` |

- 첫 번째 POST 응답 헤더에 `Mcp-Session-Id`가 포함되며, 이후 요청은 이 헤더를 전달한다.
- SSE 연결 없이 POST 하나로 요청·응답이 완결된다.

MCP Inspector로 동작 확인:
```bash
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP, URL: http://localhost:8080/mcp
# Header: X-API-Key: <API_KEY 값>
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

`deploy/Dockerfile`이 빌드 이미지 정의. 각 환경별 docker-compose는 `deploy/{dev,stg,prod}/docker-compose.yml`에 위치하며 `context: ../..`(프로젝트 루트)로 빌드한다.
