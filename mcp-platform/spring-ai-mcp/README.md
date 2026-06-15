# Spring AI MCP Server

Spring AI 1.0.0 기반 MCP 서버 샘플. Tool / Prompt / Resource 패턴과 DB 연동을 케이스별로 구현.

## 기술 스택

| 항목 | 버전 |
|------|------|
| Java | 21 |
| Spring Boot | 3.4.5 |
| Spring AI | 1.0.0 |
| Gradle | 9.2.0 |
| DB | PostgreSQL + MyBatis + JPA |

---

## 빌드 및 실행

```bash
# 빌드
./gradlew build

# 실행 (Streamable HTTP, 포트 8080)
./gradlew bootRun

# JAR 빌드
./gradlew bootJar

# 테스트
./gradlew test
```

---

## MCP 엔드포인트

```
http://localhost:8080/mcp
```

인증: 모든 요청에 `X-API-Key` 헤더 필요 (기본값: `change-me-in-production`)

```bash
# 헬스체크 (인증 불필요)
curl http://localhost:8080/actuator/health

# MCP Inspector
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP
# URL: http://localhost:8080/mcp
# Header: X-API-Key: change-me-in-production
```

---

## Tool 목록

### SampleTool — 6가지 패턴

| 메서드 | 패턴 |
|--------|------|
| `sampleGreet(name)` | 단순 문자열 반환 |
| `sampleGetProduct(productId)` | inner Record 반환 |
| `sampleCreateOrder(productId, quantity, urgent)` | 다중 파라미터 + `@ToolParam` |
| `sampleGetTodo(id)` | RestClient 외부 API 호출 |
| `sampleValidateAge(age)` | 입력 검증 — 오류를 문자열로 반환 |
| `sampleAddMemo` / `sampleGetMemo` | InMemory CRUD |

### SampleDbTool — DB 연동

MyBatis + JPA로 `sample_item` 테이블 CRUD.

---

## 프로젝트 구조

```
src/main/java/com/example/mcpserver/
├── McpServerApplication.java
├── global/
│   ├── config/McpConfig.java          # Tool 일괄 등록
│   └── security/
│       ├── ApiKeyFilter.java
│       └── SecurityConfig.java
└── sample/
    ├── tool/SampleTool.java           # 6가지 Tool 패턴
    ├── tool/SampleDbTool.java         # DB Tool
    ├── prompt/SamplePrompt.java       # Prompt 등록
    ├── resource/SampleResource.java   # Resource 등록
    └── db/
        ├── entity/SampleItem.java
        ├── mapper/SampleItemMapper.java
        └── repository/SampleItemRepository.java
```

---

## 환경별 배포

`deploy/README.md` 참고.

## Claude Desktop 연동 (stdio)

`build.gradle` 의존성 변경:
```groovy
// 제거
implementation 'org.springframework.ai:spring-ai-starter-mcp-server-webmvc'
// 추가
implementation 'org.springframework.ai:spring-ai-starter-mcp-server-stdio'
```

`application.yml` 추가:
```yaml
spring:
  main:
    web-application-type: none
```

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
