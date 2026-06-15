# CLAUDE.md — platform-server

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

인증·사용자·MCP API 키를 관리하는 Spring Boot 서비스.  
PostgreSQL `llmonl` 스키마를 소유하며, JWT를 발급해 admin-front 로그인을 처리하고, spring-ai-mcp의 API 키 검증 요청을 공개 엔드포인트(`/api/v1/api-keys/validate`)로 응답합니다.

## Stack

| 항목 | 내용 |
|------|------|
| 언어 | Java 21 |
| 프레임워크 | Spring Boot 3.4 |
| 빌드 | Gradle (Groovy DSL) |
| DB 스키마 | JPA `ddl-auto: validate` — 테이블은 `deploy/initdb/init.sh` 로 생성 |
| 인증 | JWT HS256 (JJWT 0.12) |
| API 문서 | springdoc-openapi 2.7 |

## Common Commands

```powershell
# 의존성 다운로드 + 컴파일
./gradlew compileJava

# 테스트 (H2 인메모리 DB, application-test.yml, ddl-auto: create-drop)
./gradlew test

# 단일 테스트 클래스 실행
./gradlew test --tests "com.sehoon.platform.auth.AuthServiceTest"

# 실행 가능 JAR 생성 (build/libs/*.jar)
./gradlew bootJar

# 로컬 실행 (PowerShell)
$env:APP_ENV='local'
$env:JWT_SECRET_KEY='your-32-char-secret-key-here!!'
$env:POSTGRES_HOST='localhost'; $env:POSTGRES_PORT='5432'
$env:POSTGRES_DB='llm_db'; $env:POSTGRES_USER='postgres'; $env:POSTGRES_PASSWORD='postgres'
./gradlew bootRun
```

Swagger UI: `http://localhost:8080/swagger-ui/index.html`

> **로컬 실행 전**: `llmonl` 스키마와 테이블이 존재해야 합니다 (`ddl-auto: validate`).  
> `deploy/initdb/init.sh` 를 로컬 PostgreSQL에 수동으로 실행하거나, `deploy/` compose로 DB만 먼저 기동:  
> ```bash
> cd deploy && docker compose up -d db
> ```

## Architecture

```
src/main/java/com/sehoon/platform/
├── PlatformApplication.java
├── common/
│   ├── config/
│   │   ├── SecurityConfig.java           # Spring Security + JWT 필터 체인
│   │   └── OpenApiConfig.java            # Swagger Bearer Auth 설정
│   ├── security/
│   │   ├── JwtProvider.java              # 토큰 발급·검증 (HS256)
│   │   └── JwtAuthenticationFilter.java  # 요청당 JWT 파싱 → SecurityContext
│   ├── domain/BaseEntity.java            # createdAt / updatedAt (JPA Auditing)
│   ├── dto/ApiResponse.java              # 공통 응답 래퍼 {success, message, data}
│   └── exception/
│       ├── ErrorCode.java                # 에러 코드 enum (HTTP 상태 포함)
│       ├── BusinessException.java        # 도메인 예외
│       └── GlobalExceptionHandler.java
├── auth/
│   ├── domain/   ApiKey, RefreshToken
│   ├── repository/
│   ├── service/  AuthService, ApiKeyService
│   ├── dto/      LoginRequest, LoginResponse, RegisterRequest,
│   │             ApiKeyValidateRequest, ApiKeyValidateResponse, ...
│   └── api/      AuthController, ApiKeyController
└── user/
    ├── domain/   User, UserRole (SUPERADMIN | ADMIN | USER)
    ├── repository/UserRepository
    ├── service/  UserService
    ├── dto/      UserResponse, UserUpdateRequest
    └── api/      UserController
```

## 인증

JWT HS256 단일 방식. `JWT_SECRET_KEY` 환경변수 필수.

`/api/v1/api-keys/validate` 는 공개 엔드포인트로, spring-ai-mcp가 MCP 클라이언트의 API 키를 검증할 때 호출한다. JWT 없이 `{ key: "sk-..." }` 만 전달하면 `{ keyId, userId, username, role }` 을 반환한다.

## API Endpoints

| Method | Path | 권한 | 설명 |
|--------|------|------|------|
| POST | `/api/v1/auth/register` | 공개 | 회원가입 |
| POST | `/api/v1/auth/login` | 공개 | 로그인 — access + refresh 토큰 발급 |
| POST | `/api/v1/auth/refresh` | 공개 | 액세스 토큰 갱신 |
| POST | `/api/v1/auth/logout` | 공개 | 로그아웃 (refresh 토큰 폐기) |
| GET | `/api/v1/users/me` | 인증 | 내 정보 조회 |
| PATCH | `/api/v1/users/me` | 인증 | 내 정보 수정 |
| GET | `/api/v1/users` | ADMIN+ | 전체 사용자 목록 |
| GET | `/api/v1/users/{id}` | ADMIN+ | 특정 사용자 조회 |
| DELETE | `/api/v1/users/{id}` | SUPERADMIN | 사용자 비활성화 |
| GET | `/api/v1/api-keys` | 인증 | 내 API 키 목록 (key 마스킹됨) |
| POST | `/api/v1/api-keys` | 인증 | API 키 생성 (전체 키는 1회만 반환) |
| DELETE | `/api/v1/api-keys/{id}` | 인증 | API 키 폐기 |
| POST | `/api/v1/api-keys/validate` | 공개 | API 키 유효성 검증 (spring-ai-mcp 내부 호출) |

## JWT 구조

platform-server가 발급하는 JWT payload:

```json
{
  "sub": "1",
  "username": "john",
  "email": "john@example.com",
  "role": "USER",
  "iat": 1234567890,
  "exp": 1234568490,
  "jti": "uuid"
}
```

## Database

PostgreSQL `llmonl` 스키마. JPA `ddl-auto: validate`로 기동 시 스키마 검증.

| 테이블 | 설명 |
|--------|------|
| `users` | 사용자 계정 (role: SUPERADMIN \| ADMIN \| USER) |
| `api_key` | MCP 클라이언트용 API 키 (`sk-` 접두사, 32바이트 랜덤) |
| `refresh_token` | Refresh 토큰 (폐기 가능) |

## Environment Variables

`.env.example` 참고.

| 변수 | 설명 |
|------|------|
| `JWT_SECRET_KEY` | JWT 서명 시크릿키 (32자 이상) |
| `POSTGRES_HOST` | DB 호스트 (Docker compose: `db`, 로컬: `localhost`) |
| `POSTGRES_PORT` | DB 포트 (기본 5432) |
| `POSTGRES_DB` | DB명 (`llm_db`) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | DB 인증 |
| `POSTGRES_SCHEMA` | 스키마명 (`llmonl`) |
| `APP_ENV` | 실행 환경: `local` \| `development` \| `staging` \| `production` |

## Spring Profile → 환경 파일 매핑

| APP_ENV | 로드되는 파일 | ddl-auto |
|---------|--------------|----------|
| `local` | `application-local.yml` | none |
| `development` | `application-development.yml` | validate |
| `staging` | `application-staging.yml` | validate |
| `production` | `application-production.yml` | validate |
| `test` | `application-test.yml` (H2 인메모리) | create-drop |

## Code Style

- 패키지: `com.sehoon.platform`
- 레이어 패턴: `api/` → `service/` → `domain/` + `repository/` + `dto/`
- 공통 응답: `ApiResponse<T>` record — `ok(data)` / `ok(message, data)` / `fail(message)`
- 예외: `BusinessException(ErrorCode)` → `GlobalExceptionHandler`
