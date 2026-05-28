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

# 테스트
./gradlew test

# 단일 테스트 실행
./gradlew test --tests "com.example.mcpserver.McpServerApplicationTests"
```

## Architecture

Spring AI 1.0.0 기반 MCP 서버. 도메인별 Tool 클래스를 `McpConfig`에서 `MethodToolCallbackProvider`로 일괄 등록하는 구조.

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

### Streamable HTTP 엔드포인트 및 검증

```
http://localhost:8080/mcp
```

MCP Inspector로 동작 확인:
```bash
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP, URL: http://localhost:8080/mcp
# Header: X-API-Key: change-me-in-production
```

### Claude Desktop 연동 (stdio 모드)

`%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "spring-ai-mcp": {
      "command": "java",
      "args": ["-jar", "/absolute/path/to/spring-ai-mcp-0.0.1-SNAPSHOT.jar"]
    }
  }
}
```
