# Spring AI MCP Server

Spring AI를 사용하여 MCP(Model Context Protocol) 서버를 구축한 샘플 프로젝트입니다.  
도메인 기반 패키지 구조로 구성하며, 실제 개발에서 자주 사용되는 Tool 패턴을 케이스별로 구현합니다.

---

## 기술 스택

| 항목 | 버전 |
|------|------|
| Java | 21 |
| Spring Boot | 3.4.5 |
| Spring AI | 1.0.0 |
| Gradle (Groovy DSL) | 8.x |
| Lombok | latest |

---

## 도메인별 Tool 설명

| 도메인 | 클래스 | 핵심 패턴 |
|--------|--------|-----------|
| `greeting` | `GreetingTool` | 단순 문자열 반환 |
| `product` | `ProductTool` | 객체(Record) 반환 — MCP가 JSON으로 자동 직렬화 |
| `order` | `OrderTool` | 다중 파라미터 + `@ToolParam(description=...)` 명시 |
| `todo` | `TodoTool` | RestClient로 외부 API 호출 + try-catch 오류 처리 |
| `validation` | `AgeValidationTool` | 입력값 검증 — 오류를 문자열로 반환하여 LLM에 전달 |
| `memo` | `MemoTool` + `MemoService` | Spring Bean 생성자 주입 + InMemory CRUD |

### Tool 메서드 목록

| Tool 메서드 | 설명 |
|-------------|------|
| `greet(name)` | 이름을 받아 인사말 반환 |
| `getProduct(productId)` | 상품 ID로 상품 정보(Record) 반환 |
| `createOrder(productId, quantity, urgent)` | 주문 생성 — 긴급 여부에 따라 20% 할증 |
| `getTodo(id)` | JSONPlaceholder API에서 Todo 조회 |
| `validateAge(age)` | 나이 유효성 검사 — 결과 또는 오류 메시지 반환 |
| `addMemo(key, content)` | 메모 저장 |
| `getMemo(key)` | 키로 메모 조회 |

---

## 빌드 및 실행

```bash
# 빌드
./gradlew build

# 실행 (SSE transport, 포트 8080)
./gradlew bootRun

# 테스트
./gradlew test
```

서버가 시작되면 SSE endpoint가 활성화됩니다.

```
http://localhost:8080/sse
```

---

## Claude Desktop 연동 (stdio 방식)

### 1. stdio transport로 전환

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

### 2. JAR 빌드

```bash
./gradlew bootJar
```

### 3. Claude Desktop 설정

`claude_desktop_config.json` (`~/Library/Application Support/Claude/` 또는 `%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "spring-ai-mcp": {
      "command": "java",
      "args": [
        "-jar",
        "/absolute/path/to/spring-ai-mcp-0.0.1-SNAPSHOT.jar"
      ]
    }
  }
}
```

---

## SSE 방식 연동

SSE transport를 사용하는 MCP 클라이언트의 경우 아래 URL로 연결합니다.

```
http://localhost:8080/sse
```

MCP Inspector(npx @modelcontextprotocol/inspector) 등으로 동작을 확인할 수 있습니다.

```bash
npx @modelcontextprotocol/inspector
# Transport: SSE
# URL: http://localhost:8080/sse
```

---

## 프로젝트 구조

```
src/main/java/com/example/mcpserver/
├── McpServerApplication.java
├── global/config/
│   └── McpConfig.java              # 전체 Tool Bean MCP 일괄 등록
├── greeting/tool/
│   └── GreetingTool.java           # Case 1: 단순 문자열 반환
├── product/
│   ├── tool/ProductTool.java       # Case 2: 객체(Record) 반환
│   └── dto/ProductInfo.java
├── order/
│   ├── tool/OrderTool.java         # Case 3: 다중 파라미터
│   └── dto/OrderResult.java
├── todo/
│   ├── tool/TodoTool.java          # Case 4: 외부 API 호출
│   └── dto/TodoInfo.java
├── validation/tool/
│   └── AgeValidationTool.java      # Case 5: 예외 처리
└── memo/
    ├── tool/MemoTool.java          # Case 6: Spring Bean 주입
    ├── service/MemoService.java
    └── dto/MemoInfo.java
```
