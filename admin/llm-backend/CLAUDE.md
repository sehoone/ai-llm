# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run (dev profile with H2 in-memory DB)
./gradlew bootRun

# Build JAR
./gradlew bootJar

# Run tests
./gradlew test

# Run a single test class
./gradlew test --tests "com.multicampus.llmbackend.domain.user.service.UserServiceTest"

# Docker (prod profile with PostgreSQL)
cp .env.example .env   # fill in secrets first
docker-compose up -d
docker-compose down -v # stop and wipe volumes
```

## Architecture

**Base package:** `com.multicampus.llmbackend`
**Spring Boot version:** 4.0.5 (Spring Framework 7, Java 21)

The codebase follows a domain-oriented package structure with two top-level layers:

### `global/` — Cross-cutting infrastructure
- **`jwt/`** — `JwtProvider` builds and validates HMAC-SHA tokens using `jjwt 0.12.6`. `JwtFilter` (`OncePerRequestFilter`) extracts the Bearer token from `Authorization` header and populates `SecurityContext`. The filter is registered manually in `SecurityConfig`, not as a Spring bean.
- **`config/SecurityConfig`** — Stateless, session-less filter chain. Public paths are listed in `WHITE_LIST` — add new unauthenticated paths here. `PasswordEncoder` (BCrypt) bean lives here.
- **`config/JpaConfig`** — Sole purpose is `@EnableJpaAuditing` to activate `@CreatedDate` / `@LastModifiedDate` on entities.
- **`config/SwaggerConfig`** — Registers a global `BearerAuth` security scheme so every Swagger endpoint has a JWT input field. Available at `/swagger-ui.html`.
- **`exception/`** — `CustomException` wraps an `ErrorCode` enum entry (HTTP status + namespaced code string + Korean message). `GlobalExceptionHandler` (@RestControllerAdvice) catches `CustomException`, `MethodArgumentNotValidException`, and fallback `Exception`.
- **`response/ApiResponse<T>`** — Universal response envelope: `{ success, code, message, data }`. Use `ApiResponse.success(data)` or `ApiResponse.error(ErrorCode)`.

### `domain/` — Feature modules
Each domain owns `controller → service → repository → entity + dto`. No cross-domain repository injection; go through a service if cross-domain data is needed.

- **`user/`** — `POST /api/v1/auth/signup` and `POST /api/v1/auth/login`. Entity maps to table `users`. `User.Role` enum: `USER`, `ADMIN`. The role is embedded in the Access Token as claim `"role"` and surfaced as `ROLE_USER` / `ROLE_ADMIN` in Spring Security authorities.
- **`health/`** — `GET /health` returns `ApiResponse<String>("OK")`. No auth required.

### JWT flow
```
Login → UserService → JwtProvider.generateAccessToken(email, role)
                    → JwtProvider.generateRefreshToken(email)
Request → JwtFilter.doFilterInternal → JwtProvider.validateToken
                                      → JwtProvider.getAuthentication → SecurityContext
```
JWT secret is injected via `${jwt.secret}` (Base64-encoded, ≥256-bit). Expiry values are in milliseconds (`jwt.access-token-expiry`, `jwt.refresh-token-expiry`).

### Profiles
| Profile | DB | DDL | Activated by |
|---------|-----|-----|-------------|
| `dev` (default) | H2 in-memory (PostgreSQL mode) | `create-drop` | `application.yml` default |
| `prod` | PostgreSQL via env vars | `validate` | `SPRING_PROFILES_ACTIVE=prod` |

`application-prod.yml` is git-ignored. `.env` is git-ignored; use `.env.example` as the template.

### JPA vs MyBatis 역할 분담

이 프로젝트는 JPA와 MyBatis를 함께 사용합니다.

| 용도 | 기술 |
|------|------|
| 단순 CRUD, 엔티티 저장/수정/삭제 | JPA (`UserRepository extends JpaRepository`) |
| 복잡한 조건 검색, 페이징, 다중 테이블 JOIN | MyBatis (`UserMapper`, XML) |

**MyBatis 파일 위치 규칙**
- Mapper 인터페이스: `domain/{name}/repository/{Name}Mapper.java` — `@Mapper` 어노테이션 필수
- XML: `src/main/resources/mapper/{name}/{Name}Mapper.xml`
- XML `namespace`는 Mapper 인터페이스의 FQCN과 정확히 일치해야 합니다.
- 동적 조건 절은 `<sql id="...">` + `<include refid="...">` 로 재사용하세요.

**MyBatis 전역 설정** (`application.yml`)
- `map-underscore-to-camel-case: true` → DB 컬럼 `created_at` → Java 필드 `createdAt` 자동 매핑
- `mapper-locations: classpath:mapper/**/*.xml`

**ResultMap DTO**는 JPA 엔티티와 분리된 별도 클래스를 사용합니다 (예: `UserListItem`). JPA 엔티티를 MyBatis 결과로 직접 매핑하지 마세요.

### Adding a new domain
1. Create `domain/{name}/{controller,service,repository,entity,dto}/` packages.
2. Add new `ErrorCode` entries with the domain prefix (e.g. `O001` for orders).
3. If the endpoint needs no auth, add its path pattern to `SecurityConfig.WHITE_LIST`.
4. For complex queries, create `{Name}Mapper.java` + `src/main/resources/mapper/{name}/{Name}Mapper.xml`.
