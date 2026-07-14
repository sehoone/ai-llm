# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

pgvector POC — 텍스트 임베딩 저장과 코사인 유사도 검색을 실증하는 두 서비스:

```
[Next.js :3000]  ←→  [Spring Boot :8080]  ←→  [PostgreSQL + pgvector :5432]
  admin-front           vector-server              poc_vector DB
```

기본 계정: `admin@poc.com` / `admin1234`

---

## 로컬 개발 실행

```powershell
# 1. PostgreSQL + pgvector 시작 (vector-server/docker-compose.yml)
cd vector-server
docker compose up -d

# 2. Spring Boot 실행 (schema.sql / data.sql 자동 실행)
$env:AZURE_OPENAI_API_KEY='your-api-key'
$env:AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com'
$env:AZURE_OPENAI_DEPLOYMENT_NAME='text-embedding-3-small'
# $env:AZURE_OPENAI_API_VERSION='2024-02-01'  # 기본값, 필요 시 변경
./gradlew bootRun    # 로컬 Gradle 7.6.4+ 필요. 없으면 → poc-deploy/ Docker 사용

# 3. Next.js 프론트엔드
cd ../admin-front
pnpm install         # 최초 1회
pnpm dev             # http://localhost:3000
```

---

## vector-server (Spring Boot)

**스택**: Java 1.8 · Spring Boot 2.7.18 · MyBatis 2.3.x · PostgreSQL JDBC 42 · jjwt 0.11.5

```powershell
./gradlew bootRun    # :8080
./gradlew bootJar    # fat jar → build/libs/
./gradlew test       # JUnit 5
```

### 핵심 제약사항

- **Java 1.8 전용** — `var`, record, text block 사용 불가
- **MyBatis XML 전용** — 모든 SQL은 `src/main/resources/mapper/*.xml`. 어노테이션 방식 금지
- **Spring Security**: `WebSecurityConfigurerAdapter` 상속 방식 (Boot 2.7). Boot 3의 람다 DSL 사용 불가
- `schema.sql` + `data.sql`은 매 기동 시 실행 (`mode=always`) → `IF NOT EXISTS` / `WHERE NOT EXISTS` 필수
- Docker 배포 시 `SPRING_SQL_INIT_MODE=never` → `poc-deploy/init.sql`이 스키마 담당
- **TLS 1.2 강제**: Java 8과 Azure OpenAI 간 TLS 1.3 협상 실패 이슈 → `JAVA_TOOL_OPTIONS=-Dhttps.protocols=TLSv1.2 -Djdk.tls.client.protocols=TLSv1.2`로 회피 (Docker 배포 환경 포함)

### 패키지 구조

```
com.poc.vectorsearch
├── config/     JwtConfig, JwtFilter, SecurityConfig, OpenAiConfig
├── handler/    VectorTypeHandler  ← float[] ↔ PostgreSQL vector
├── controller/ AuthController, EmbeddingController, SearchController, GlobalExceptionHandler
├── service/    AuthService, EmbeddingService, SearchService, OpenAiEmbeddingService
├── mapper/     UserMapper, DocumentMapper  (인터페이스만)
├── domain/     User, Document, EmbeddingVector  (float[] 래퍼, 직렬화·파싱 집중)
└── dto/        Login*, Embedding*, Bulk*, Search*, PageResponse<T>
```

### API 엔드포인트

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| POST | `/api/v1/auth/login` | — | JWT 발급 (`accessToken`, `refreshToken`, `user`) |
| POST | `/api/v1/auth/refresh` | — | POC 스텁 |
| POST | `/api/v1/auth/logout` | — | POC 스텁 |
| POST | `/api/v1/embeddings` | JWT | 단건 임베딩 생성 (Azure OpenAI 호출 후 저장) |
| GET  | `/api/v1/embeddings` | JWT | 문서 목록 페이지 (`?page=0&size=10`) → `PageResponse<EmbeddingResponse>` |
| POST | `/api/v1/embeddings/batch` | JWT | JSON 배열 일괄 임베딩 (`id`, `title`, `desc`) |
| DELETE | `/api/v1/embeddings/{id}` | JWT | 문서 삭제 |
| DELETE | `/api/v1/embeddings` | JWT | 전체 문서 삭제 |
| POST | `/api/v1/search` | JWT | 코사인 유사도 검색 (`query`, `topK` 1~20, `threshold` 0.0~1.0 기본 0.7) |

### 예외 처리

`GlobalExceptionHandler` (`@RestControllerAdvice`):
- `IllegalArgumentException` → 401 (인증 실패 메시지)
- `MethodArgumentNotValidException` → 400 (필드별 유효성 오류)
- `RuntimeException` → 500

### pgvector 핵심

`VectorTypeHandler`: MyBatis ↔ pgvector 브리지
- **쓰기**: `float[]` → `PGvector` → `Types.OTHER`로 전달 (DB가 `::vector` 캐스트)
- **읽기**: `getString()` → `EmbeddingVector.parse()` → `float[]`
- XML 매퍼에서 `<=>` 연산자는 반드시 `<![CDATA[ <=> ]]>`로 감쌀 것

### Azure OpenAI 연동

`OpenAiEmbeddingService` — RestTemplate 직접 호출 (SDK 없음):
- 인증: `api-key: {key}` 헤더 (`Bearer` 아님)
- URL: `{endpoint}/openai/deployments/{deployment-name}/embeddings?api-version={api-version}`
- Request body에 `model` 필드 없음 (배포 이름이 URL에 포함)
- 기본 모델: `text-embedding-3-small` (1536차원) — 모델 변경 시 `vector(1536)` 컬럼도 재생성 필요

### 임베딩 텍스트 처리

- 단건 생성: `content`만 임베딩. `title`은 저장만 됨 (`title + " - " + content` 방식이 검색 품질에 유리)
- 일괄 업로드: `desc` 필드가 임베딩 텍스트이자 DB `content`로 저장됨. `id`는 참조용 식별자 (DB 저장 안 됨)
- `EmbeddingService.bulkCreate()`: 건별 독립 처리 — 한 건 실패해도 나머지 계속 진행

---

## admin-front (Next.js)

**스택**: Next.js 16 App Router · TypeScript strict · pnpm · Tailwind CSS v4 · shadcn/ui · TanStack Query v5 · React Hook Form + Zod v4

```bash
pnpm dev            # :3000
pnpm build          # standalone 빌드
pnpm lint           # ESLint
pnpm format         # Prettier
pnpm exec tsc --noEmit  # 타입 체크
```

### 환경 변수

`.env.local` (로컬 개발):
```
NEXT_PUBLIC_API_URL=http://localhost:8080
```
Axios baseURL = `${NEXT_PUBLIC_API_URL}/api/` → `api.post('v1/embeddings')` = `POST http://localhost:8080/api/v1/embeddings`

`.env.production` (Docker 배포 빌드용):
```
NEXT_PUBLIC_API_URL=   # 빈값 → /api/* 상대경로 → Nginx 경유
API_URL=http://vector-server:8080
```

### 라우트 구조

- `(auth)/sign-in` — 공개 로그인 페이지
- `(authenticated)/` — 쿠키의 `access_token` 검증, 없으면 `/sign-in` 리다이렉트
- `(errors)/` — 401, 403, 500, 503

### 피처

`src/features/<name>/index.tsx` → `src/app/(authenticated)/<name>/page.tsx` 1:1 대응

| 피처 | 경로 | 기능 |
|------|------|------|
| `embeddings` | `/embeddings` | Tabs: 단건 입력 / JSON 파일 일괄 업로드 + 결과 확인. 문서 목록(페이지네이션) + 전체/단건 삭제 |
| `search` | `/search` | 검색어 입력 → 유사도 카드 결과 (점수 바 표시). 결과 클릭 시 Dialog로 전문 표시 |

### API 레이어 (`src/api/`)

- `auth.ts` — login, refresh, logout
- `embeddings.ts` — createEmbedding, listEmbeddings, deleteEmbedding, deleteAllEmbeddings, bulkUploadEmbeddings, searchEmbeddings

공유 Axios 인스턴스(`axios.ts`) 인터셉터:
- 만료 2초 전 토큰 선제 갱신
- 갱신 중 요청 큐잉 (`failedQueue`)
- 401 시 1회 재시도 → 실패 시 `/sign-in` 리다이렉트

### 피처 추가 패턴

1. `src/features/<name>/index.tsx` 생성 (`'use client'`)
2. `src/app/(authenticated)/<name>/page.tsx` 생성
3. `src/components/layout/data/sidebar-data.ts`에 메뉴 항목 추가
4. `src/api/<name>.ts` 생성

### 코드 규칙

- `console.*` 금지 → `import { logger } from '@/lib/logger'` 사용
- Zod: numeric 필드에 `z.coerce.number()` 금지 → `z.number()` 사용 (RHF 제네릭 타입 오류 방지)
- Zod v4: `ZodError.errors` → `ZodError.issues`
- `src/components/ui/` — ESLint 적용 제외 (shadcn 생성 파일)
- Prettier import 정렬: `react → 서드파티 → @/api → @/stores → @/lib → @/context → @/hooks → @/components → @/features → 상대경로`

---

## poc-deploy (Docker 배포)

```bash
cd poc-deploy
cp .env.example .env   # AZURE_OPENAI_* 등 필수 값 입력

bash deploy.sh up       # 전체 빌드 & 시작 (Nginx :80)
bash deploy.sh init-db  # DB 스키마 수동 초기화 (최초 1회)
bash deploy.sh logs [service]
bash deploy.sh restart
bash deploy.sh clean    # 볼륨 포함 완전 삭제
```

**서비스 의존 순서**: postgres → vector-server → admin-front → nginx

**스키마 담당 분리**:
- Docker 배포: `poc-deploy/init.sql` (수동 실행, `bash deploy.sh init-db`)
- 로컬 개발: Spring Boot `schema.sql` / `data.sql` (자동)

**헬스체크**: `wget -qSO /dev/null http://localhost:8080/api/v1/auth/login 2>&1 | grep -q HTTP`
(Alpine busybox wget은 서버 응답 시에도 exit 1 반환 → HTTP 헤더 존재 여부로 판단)

**Dockerfile** (`vector-server`): `gradlew` 없으므로 `gradle:7.6.4-jdk8` 이미지로 직접 빌드

---

## DB 스키마

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY, username VARCHAR(100), email VARCHAR(255) UNIQUE,
    password VARCHAR(255),  -- BCrypt ($2b$10$...)
    role VARCHAR(50) DEFAULT 'USER', created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY, title VARCHAR(500), content TEXT,
    embedding vector(1536),  -- text-embedding-3-small
    model VARCHAR(100), created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX documents_embedding_idx ON documents
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

`embedding` 차원(1536)은 Azure 배포 모델에 종속 — 모델 변경 시 컬럼 재생성 필요.
차원이 바뀌면 `schema.sql`과 `poc-deploy/init.sql` 두 파일을 모두 수정하고 DB에서 직접 컬럼 재생성 필요 (`IF NOT EXISTS`로 인해 자동 수정 안 됨).
