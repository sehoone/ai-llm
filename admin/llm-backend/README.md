# LLM Backend

Spring Boot 4 기반 REST API 서버입니다.

## 기술 스택

- Java 21
- Spring Boot 4.0.5
- Spring Security + JWT
- Spring Data JPA + Hibernate
- PostgreSQL (운영) / H2 (개발)
- Lombok
- Springdoc OpenAPI (Swagger)

## 프로젝트 구조

```
src/main/java/com/multicampus/llmbackend/
├── domain/
│   ├── health/         # 헬스체크
│   └── user/           # 사용자 도메인
│       ├── controller/
│       ├── service/
│       ├── repository/
│       ├── entity/
│       └── dto/
└── global/
    ├── config/         # Security, Swagger, JPA 설정
    ├── exception/      # GlobalExceptionHandler, CustomException, ErrorCode
    ├── response/       # ApiResponse 공통 응답 래퍼
    └── jwt/            # JwtProvider, JwtFilter
```

## 로컬 실행 (Dev 프로필 - H2)

```bash
./gradlew bootRun
```

- 기본 프로필: `dev` (H2 인메모리 DB 사용)
- H2 콘솔: http://localhost:8080/h2-console
- Swagger UI: http://localhost:8080/swagger-ui.html

## Docker 실행 (Prod 프로필 - PostgreSQL)

### 1. 환경변수 파일 준비

```bash
cp .env.example .env
# .env 파일을 열어 DB 비밀번호, JWT 시크릿 등 설정
```

JWT 시크릿 키 생성 (권장):
```bash
openssl rand -base64 64
```

### 2. 컨테이너 실행

```bash
docker-compose up -d
```

### 3. 컨테이너 중지

```bash
docker-compose down
```

DB 볼륨까지 초기화하려면:
```bash
docker-compose down -v
```

## API 엔드포인트

| Method | URL | 설명 | 인증 필요 |
|--------|-----|------|----------|
| GET | /health | 헬스체크 | X |
| POST | /api/v1/auth/signup | 회원가입 | X |
| POST | /api/v1/auth/login | 로그인 | X |

### 회원가입 예시

```json
POST /api/v1/auth/signup
{
  "email": "user@example.com",
  "password": "password123",
  "name": "홍길동"
}
```

### 로그인 예시

```json
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}
```

응답:
```json
{
  "success": true,
  "code": "200",
  "message": "OK",
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
    "refreshToken": "eyJhbGciOiJIUzI1NiJ9...",
    "tokenType": "Bearer"
  }
}
```

### 인증이 필요한 API 호출

```
Authorization: Bearer {accessToken}
```

## 환경별 프로필

| 프로필 | 설명 | DB |
|--------|------|----|
| `dev` (기본) | 로컬 개발 | H2 인메모리 |
| `prod` | 운영 환경 | PostgreSQL (환경변수) |

특정 프로필로 실행:
```bash
./gradlew bootRun --args='--spring.profiles.active=prod'
```
