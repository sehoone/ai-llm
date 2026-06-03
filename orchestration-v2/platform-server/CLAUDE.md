# CLAUDE.md — platform-server

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

인증·사용자·LLM 리소스 설정을 담당하는 Spring Boot 서비스.  
orchestrator-server(FastAPI)와 동일한 PostgreSQL DB(`llmonl` 스키마)를 공유하며,  
JWT를 발급하여 두 서버가 같은 시크릿으로 검증합니다.

## Stack

| 항목 | 내용 |
|------|------|
| 언어 | Java 21 |
| 프레임워크 | Spring Boot 3.4 |
| 빌드 | Gradle (Groovy DSL) |
| DB 스키마 | JPA `ddl-auto: validate` — 테이블은 수동 생성 또는 `deploy/postgres/init.sql` |
| 인증 | JWT HS256 (JJWT 0.12) 또는 Keycloak RS256 (`AUTH_MODE` 환경변수로 전환) |
| API 문서 | springdoc-openapi 2.7 |

## Common Commands

```powershell
# 의존성 다운로드 + 컴파일
./gradlew compileJava

# 테스트 (H2 인메모리 DB, application-test.yml, ddl-auto: create-drop)
./gradlew test

# 단일 테스트 클래스 실행
./gradlew test --tests "com.llmonl.platform.auth.AuthServiceTest"

# 실행 가능 JAR 생성 (build/libs/*.jar)
./gradlew bootJar

# 로컬 실행
$env:APP_ENV='local'
$env:JWT_SECRET_KEY='your-32-char-secret-key-here!!'
$env:POSTGRES_HOST='localhost'; $env:POSTGRES_PORT='8066'
$env:POSTGRES_DB='mydb'; $env:POSTGRES_USER='postgres'; $env:POSTGRES_PASSWORD='postgres'
./gradlew bootRun
```

Swagger UI: `http://localhost:8080/swagger-ui/index.html`

> **로컬 실행 전**: DB에 `llmonl` 스키마와 테이블이 존재해야 합니다 (`ddl-auto: none`).  
> 테이블 생성 SQL은 `deploy/postgres/init.sql` + 엔티티 DDL을 직접 실행.

## Architecture

```
src/main/java/com/llmonl/platform/
├── PlatformApplication.java
├── common/
│   ├── config/
│   │   ├── SecurityConfig.java           # Spring Security + 인증 모드별 필터 체인
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
│   ├── service/  AuthService, ApiKeyService, KeycloakAuthService
│   ├── dto/      LoginRequest, LoginResponse, RegisterRequest, ...
│   └── api/      AuthController, ApiKeyController
├── user/
│   ├── domain/   User, UserRole
│   ├── repository/UserRepository
│   ├── service/  UserService
│   ├── dto/      UserResponse, UserUpdateRequest
│   └── api/      UserController
└── llmresource/
    ├── domain/   LlmResource
    ├── repository/LlmResourceRepository
    ├── service/  LlmResourceService
    ├── dto/      LlmResourceCreateRequest, LlmResourceUpdateRequest, LlmResourceResponse
    └── api/      LlmResourceController
```

## 인증 모드 (AUTH_MODE)

`AUTH_MODE` 환경변수로 런타임 전환:

| 값 | 동작 |
|----|------|
| `jwt` (기본) | platform-server가 HS256으로 JWT 발급·검증. `JWT_SECRET_KEY` 필수 |
| `keycloak` | Keycloak RS256 JWKS로 검증. platform-server는 사용자 동기화만 수행. `KEYCLOAK_*` 설정 필수 |

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
| GET | `/api/v1/api-keys` | 인증 | 내 API 키 목록 |
| POST | `/api/v1/api-keys` | 인증 | API 키 생성 |
| DELETE | `/api/v1/api-keys/{id}` | 인증 | API 키 폐기 |
| GET | `/api/v1/llm-resources` | ADMIN+ | LLM 리소스 목록 |
| POST | `/api/v1/llm-resources` | ADMIN+ | LLM 리소스 등록 |
| PATCH | `/api/v1/llm-resources/{id}` | ADMIN+ | LLM 리소스 수정 |
| PATCH | `/api/v1/llm-resources/{id}/toggle` | ADMIN+ | 활성/비활성 토글 |
| DELETE | `/api/v1/llm-resources/{id}` | ADMIN+ | LLM 리소스 삭제 |

## JWT 구조

platform-server가 발급하는 JWT payload:

```json
{
  "sub": "1",           // user ID (orchestrator-server의 user_id)
  "username": "john",
  "email": "john@example.com",
  "role": "USER",       // SUPERADMIN | ADMIN | MANAGER | CASHIER | USER
  "iat": 1234567890,
  "exp": 1234568490,
  "jti": "uuid"
}
```

orchestrator-server는 동일한 `JWT_SECRET_KEY`로 서명 검증 후 `sub`(user_id)를 사용합니다.

## Database

PostgreSQL `llmonl` 스키마. JPA `ddl-auto: validate`로 기동 시 스키마 검증.

| 테이블 | 설명 |
|--------|------|
| `users` | 사용자 계정 (`keycloak_id` 컬럼 포함) |
| `api_key` | API 키 |
| `refresh_token` | Refresh 토큰 (폐기 가능) |
| `llm_resource` | LLM 모델 리소스 설정 |

> orchestrator-server의 나머지 테이블(`gpt_session`, `rag_embedding` 등)은 SQLModel이 자동 생성.

## Environment Variables

`.env.example` 참고. orchestrator-server와 공유하는 필수 값:

| 변수 | 설명 |
|------|------|
| `JWT_SECRET_KEY` | **orchestrator-server와 동일해야 함** (32자 이상) |
| `POSTGRES_HOST` | DB 호스트 (Docker: `db`, 로컬: `localhost`) |
| `POSTGRES_PORT` | DB 포트 (기본 5432, Docker 외부: 8066) |
| `POSTGRES_DB` | DB명 |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | DB 인증 |
| `POSTGRES_SCHEMA` | 스키마명 (`llmonl`) |
| `APP_ENV` | 실행 환경: `local` \| `development` \| `staging` \| `production` |
| `AUTH_MODE` | `jwt` (기본) 또는 `keycloak` |

## Spring Profile → 환경 파일 매핑

| APP_ENV | 로드되는 파일 |
|---------|--------------|
| `local` | `application-local.yml` (ddl-auto: none) |
| `development` | `application-development.yml` (ddl-auto: validate) |
| `staging` | `application-staging.yml` |
| `production` | `application-production.yml` |
| `test` | `application-test.yml` (H2 인메모리, ddl-auto: create-drop) |

## Code Style

- 패키지: `com.llmonl.platform`
- 레이어 패턴: `api/` → `service/` → `domain/` + `repository/` + `dto/`
- 공통 응답: `ApiResponse<T>` record 사용
- 예외: `BusinessException(ErrorCode)` → `GlobalExceptionHandler`
