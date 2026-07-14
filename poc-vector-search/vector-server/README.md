# vector-server

텍스트 임베딩 저장과 코사인 유사도 검색을 실증하는 Spring Boot 서버.  
Azure OpenAI로 텍스트를 벡터로 변환하고, pgvector를 통해 PostgreSQL에 저장·검색한다.

---

## 목차

1. [기술 스택](#기술-스택)
2. [아키텍처](#아키텍처)
3. [로컬 실행](#로컬-실행)
4. [API 엔드포인트](#api-엔드포인트)
5. [패키지 구조](#패키지-구조)
6. [pgvector 입문 가이드](#pgvector-입문-가이드)
7. [임베딩 데이터 설계 원칙](#임베딩-데이터-설계-원칙)
8. [모델·차원 변경 가이드](#모델차원-변경-가이드)
9. [구현 핵심 포인트](#구현-핵심-포인트)
10. [상용환경 적용 시 유의사항](#상용환경-적용-시-유의사항)

---

## 기술 스택

| 항목 | 버전 |
|------|------|
| Java | 1.8 |
| Spring Boot | 2.7.18 |
| MyBatis | 2.3.x |
| PostgreSQL JDBC | 42.x |
| pgvector Java | 0.1.x |
| jjwt | 0.11.5 |
| PostgreSQL | 16 + pgvector |

> **Java 1.8 전용** — `var`, record, text block, 람다 DSL 사용 불가.  
> MyBatis는 XML 매퍼 전용, 어노테이션 방식 금지.  
> Spring Security는 `WebSecurityConfigurerAdapter` 상속 방식 (Boot 2.7).

---

## 아키텍처

```
[클라이언트]
    │
    ▼
[JwtFilter]  →  JWT 없거나 유효하지 않으면 401
    │
    ▼
[Controller]  AuthController / EmbeddingController / SearchController
    │
    ▼
[Service]     AuthService / EmbeddingService / SearchService
    │                               │
    │                               ▼
    │                  [OpenAiEmbeddingService]
    │                  Azure OpenAI REST API 호출
    │                  텍스트 → float[1536] 반환
    │
    ▼
[MyBatis Mapper]  DocumentMapper / UserMapper
    │
    ▼
[VectorTypeHandler]  float[] ↔ PostgreSQL vector 변환
    │
    ▼
[PostgreSQL + pgvector]  vector(1536) 저장 / <=> 연산자로 유사도 검색
```

### 요청 흐름 — 검색 예시

```
POST /api/v1/search  { "query": "고양이", "topK": 5 }
  → SearchController
  → SearchService.search()
  → OpenAiEmbeddingService.embed("고양이")  →  Azure OpenAI  →  float[1536]
  → DocumentMapper.searchByVector(vector, 5)
  → SQL: SELECT ... ORDER BY embedding <=> #{queryVector} LIMIT 5
  → VectorTypeHandler: float[] → PGvector → JDBC setObject
  → pgvector가 코사인 거리 계산 후 상위 5건 반환
```

---

## 로컬 실행

### 1. PostgreSQL + pgvector 시작

```powershell
cd vector-server
docker compose up -d
```

`docker-compose.yml`이 `pgvector/pgvector:pg16` 이미지를 사용한다.  
컨테이너 최초 기동 시 `schema.sql` / `data.sql`이 자동 실행되어 테이블과 인덱스가 생성된다.

### 2. Spring Boot 실행

```powershell
$env:AZURE_OPENAI_API_KEY='your-api-key'
$env:AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com'
$env:AZURE_OPENAI_DEPLOYMENT_NAME='text-embedding-3-small'
./gradlew bootRun
```

`gradlew`가 없으면 로컬 Gradle 7.6.4 이상 설치 필요. 또는 `poc-deploy/`의 Docker 배포 사용.

### 3. 환경변수 목록

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `AZURE_OPENAI_API_KEY` | (필수) | Azure OpenAI 리소스 API 키 |
| `AZURE_OPENAI_ENDPOINT` | (필수) | `https://{resource}.openai.azure.com` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `text-embedding-3-small` | Azure 배포 이름 |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` | API 버전 |

---

## API 엔드포인트

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| POST | `/api/v1/auth/login` | — | JWT 발급 (`accessToken`, `refreshToken`, `user`) |
| POST | `/api/v1/auth/refresh` | — | POC 스텁 |
| POST | `/api/v1/auth/logout` | — | POC 스텁 |
| POST | `/api/v1/embeddings` | JWT | 단건 임베딩 생성 |
| GET | `/api/v1/embeddings` | JWT | 문서 목록 (벡터 제외) |
| POST | `/api/v1/embeddings/batch` | JWT | JSON 배열 일괄 임베딩 |
| DELETE | `/api/v1/embeddings/{id}` | JWT | 문서 삭제 |
| POST | `/api/v1/search` | JWT | 코사인 유사도 검색 |

### 요청/응답 예시

**로그인**
```json
POST /api/v1/auth/login
{ "email": "admin@poc.com", "password": "admin1234" }

→ { "accessToken": "eyJ...", "refreshToken": "...", "user": { ... } }
```

**임베딩 생성**
```json
POST /api/v1/embeddings
Authorization: Bearer eyJ...
{ "title": "고양이", "content": "고양이는 독립적인 성격을 가진 포유류입니다." }

→ { "id": 1, "title": "고양이", "content": "...", "model": "text-embedding-3-small", ... }
```

**유사도 검색**
```json
POST /api/v1/search
Authorization: Bearer eyJ...
{ "query": "강아지", "topK": 3 }

→ [
    { "id": 2, "title": "개", "score": 0.91, ... },
    { "id": 1, "title": "고양이", "score": 0.74, ... },
    ...
  ]
```

**일괄 업로드 (JSON 배열)**
```json
POST /api/v1/embeddings/batch
Authorization: Bearer eyJ...
[
  { "id": "a1", "title": "사과", "desc": "새콤달콤한 과일입니다." },
  { "id": "a2", "title": "바나나", "desc": "노란색의 열대 과일입니다." }
]

→ { "total": 2, "successCount": 2, "failedCount": 0, "results": [ ... ] }
```

> 일괄 업로드는 건별 독립 처리 — 한 건 실패해도 나머지는 계속 진행된다.

---

## 패키지 구조

```
com.poc.vectorsearch
├── config/
│   ├── JwtConfig.java          JWT 서명 키 및 만료 시간 설정
│   ├── JwtFilter.java          요청마다 Authorization 헤더 검증
│   ├── SecurityConfig.java     Spring Security 설정 (Boot 2.7 방식)
│   └── OpenAiConfig.java       Azure OpenAI 연결 정보 + URL 조합
│
├── handler/
│   └── VectorTypeHandler.java  float[] ↔ pgvector 타입 변환 (MyBatis)
│
├── controller/
│   ├── AuthController.java
│   ├── EmbeddingController.java
│   ├── SearchController.java
│   └── GlobalExceptionHandler.java  @RestControllerAdvice
│
├── service/
│   ├── AuthService.java
│   ├── EmbeddingService.java        단건/일괄 임베딩 생성·저장
│   ├── SearchService.java           쿼리 임베딩 후 유사도 검색
│   └── OpenAiEmbeddingService.java  Azure OpenAI REST 호출
│
├── mapper/
│   ├── UserMapper.java
│   └── DocumentMapper.java
│
├── domain/
│   ├── User.java
│   ├── Document.java
│   └── EmbeddingVector.java    float[] 래퍼 (직렬화·파싱 로직 집중)
│
└── dto/
    ├── LoginRequest / LoginResponse
    ├── EmbeddingRequest / EmbeddingResponse
    ├── BulkEmbeddingItem / BulkEmbeddingResponse / BulkEmbeddingResultItem
    ├── SearchRequest / SearchResult
```

---

## pgvector 입문 가이드

### 임베딩이란?

텍스트를 AI 모델이 숫자 배열(float[])로 변환한 값.

```
"고양이" → [0.12, -0.45, 0.78, 0.03, ...]  (1536개 숫자)
"강아지" → [0.11, -0.43, 0.75, 0.05, ...]  (방향이 비슷 → 의미가 유사)
"자동차" → [-0.82, 0.21, -0.33, 0.91, ...]  (방향이 다름 → 의미가 다름)
```

일반 SQL `WHERE content LIKE '%고양이%'`는 글자가 정확히 일치해야 동작한다.  
임베딩 검색은 "강아지"로 검색해도 "개", "반려동물" 같은 의미적으로 가까운 문서를 찾아낸다.

---

### pgvector 타입

```sql
-- N차원 float32 벡터 컬럼
embedding vector(1536)
```

괄호 안 숫자는 **차원 수(배열 길이)**. 모델마다 고정값이 있다.

| 모델 | 차원 |
|------|------|
| text-embedding-3-small | 1536 |
| text-embedding-ada-002 | 1536 |
| text-embedding-3-large | 3072 |

---

### 유사도 연산자

pgvector는 세 가지 거리 계산 방식을 제공한다.

| 연산자 | 이름 | 설명 | 값 범위 |
|--------|------|------|---------|
| `<=>` | 코사인 거리 | 벡터 방향 차이 (크기 무시) | 0 ~ 2 |
| `<->` | 유클리드 거리 | 절대적 거리 (크기 포함) | 0 ~ ∞ |
| `<#>` | 내적 (부호 반전) | 정규화 벡터에서 코사인과 동일 | -∞ ~ 0 |

텍스트 의미 검색에는 `<=>` (코사인 거리)가 가장 일반적이다.  
코사인은 문장 길이(벡터 크기)에 영향받지 않고 **의미(방향)**만 비교한다.

```sql
-- 가장 가까운 5건 (코사인 거리가 작을수록 유사)
SELECT title, 1 - (embedding <=> '[0.1, -0.2, ...]'::vector) AS similarity
FROM documents
ORDER BY embedding <=> '[0.1, -0.2, ...]'::vector
LIMIT 5;

-- score = 1 - 코사인 거리  →  1에 가까울수록 유사, 0에 가까울수록 무관
```

---

### 인덱스 종류와 선택 기준

인덱스 없이 검색하면 모든 행을 순차 스캔(O(N))한다.  
문서 수만 건을 넘으면 인덱스를 통한 **근사 최근접 이웃(ANN)** 탐색이 필수다.

| 인덱스 | 특징 | 적합한 상황 |
|--------|------|------------|
| **IVFFlat** | 벡터를 클러스터로 나눠 근사 탐색. 빌드 빠름, 메모리 적음 | 수만~수십만 건, 빠른 구축 우선 |
| **HNSW** | 그래프 기반. 정확도(recall) 높음. 빌드 느림, 메모리 많이 사용 | 수십만 건 이상, 정확도 우선 |

```sql
-- IVFFlat (이 POC 사용)
CREATE INDEX ON documents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- HNSW (pgvector 0.5.0+)
CREATE INDEX ON documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

---

### IVFFlat lists 튜닝

`lists`는 IVFFlat이 벡터를 나누는 클러스터 수. 권장값 = `sqrt(총 문서 수)`.

| 문서 수 | 권장 lists |
|---------|-----------|
| 1,000 | 32 |
| 10,000 | 100 |
| 100,000 | 316 |
| 1,000,000 | 1,000 |

검색 정확도를 높이려면 `probes`를 늘린다 (기본 1):
```sql
SET ivfflat.probes = 5;  -- 탐색 클러스터 수 증가 → 정확도↑, 속도↓
```

> **주의**: IVFFlat 인덱스는 데이터가 어느 정도 쌓인 뒤 생성해야 클러스터 품질이 좋다.  
> 빈 테이블에서 만든 인덱스는 나중에 `REINDEX TABLE documents;`로 재구성 권장.

---

### pgvector 차원 제한

저장(타입)과 인덱스에 각각 별도 제한이 있다.

**저장 가능 차원 (타입별)**

| 타입 | 최대 차원 | 정밀도 |
|------|----------|--------|
| `vector` | 16,000 | float32 |
| `halfvec` | 16,000 | float16 |
| `bit` | 64,000 | 1bit |

**인덱스 차원 제한 ← 실질적 병목**

| 인덱스 | `vector` 최대 | `halfvec` 최대 |
|--------|-------------|--------------|
| IVFFlat | **2,000** | 16,000 |
| HNSW | **2,000** | 16,000 |

```
text-embedding-3-small  1536차원  ✅  IVFFlat/HNSW 인덱스 사용 가능
text-embedding-3-large  3072차원  ⚠️  vector 타입으로는 ANN 인덱스 불가 → 전체 순차 스캔
```

3072차원 이상이 필요하면 `halfvec` 타입과 HNSW 인덱스 조합을 사용한다:
```sql
ALTER TABLE documents ADD COLUMN embedding halfvec(3072);
CREATE INDEX ON documents USING hnsw (embedding halfvec_cosine_ops);
```

---

## 임베딩 데이터 설계 원칙

검색 품질은 모델보다 **임베딩에 넣는 텍스트 설계**에 더 크게 달려 있다.

---

### 원칙 1 — 쿼리와 문서의 텍스트 형태를 맞춰라

임베딩 모델은 의미적 유사도로 벡터를 만든다. 쿼리와 문서가 같은 언어 패턴이어야 벡터 거리가 가까워진다.

| 상황 | 나쁜 예 | 좋은 예 |
|------|---------|---------|
| 문서가 명사 나열 | `"Python, AI, 머신러닝"` | `"Python으로 AI 머신러닝 모델을 학습시키는 방법"` |
| 쿼리가 질문형인데 문서가 단어 | 쿼리: `"파이썬 설치 방법?"` → 문서: `"설치 절차"` | 문서: `"파이썬을 설치하는 단계별 방법과 절차"` |

**제목과 내용을 합쳐서 임베딩**하면 의미가 풍부해져 검색 정확도가 올라간다:

```
{title} - {content}
예) "Python 설치 가이드 - Windows에서 Python 3.11을 설치하는 단계별 방법입니다."
```

이 POC의 `EmbeddingService`는 현재 `content`만 임베딩한다. `title + content`를 합치면 바로 효과를 볼 수 있다:

```java
// EmbeddingService.java 개선안
String textToEmbed = request.getTitle() + " - " + request.getContent();
```

---

### 원칙 2 — 청크(Chunk) 크기를 적절히 자르기

긴 문서를 통째로 임베딩하면 벡터가 너무 많은 의미를 담아 희석된다.

- **권장 크기**: 200~500 토큰 (한국어 기준 약 100~250자)
- **기준점**: 문단 경계로 자르기 (문장 중간 X)
- **오버랩**: 앞뒤 청크의 20~30%를 겹치게 저장 → 문맥 단절 방지

```
[청크 1] "Spring Boot는 설정을 자동화해 빠르게 서버를 만들 수 있다. 의존성은 build.gradle에 추가한다."
[청크 2] "의존성은 build.gradle에 추가한다. 예를 들어 spring-boot-starter-web을 추가하면 REST API를 만들 수 있다."
          ↑ 앞 청크 끝부분 반복 (오버랩)
```

---

### 원칙 3 — 메타데이터를 텍스트에 포함하기

카테고리, 태그, 섹션 제목을 앞에 붙이면 같은 도메인 내 검색 정확도가 크게 오른다.

```
나쁨: "의존성을 추가합니다."
좋음: "[Spring Boot 설정] build.gradle에 spring-boot-starter-web 의존성을 추가하는 방법"
```

도메인이 섞인 데이터셋(예: 요리 + 프로그래밍)에서는 메타데이터 없이는 같은 "재료 추가"라는 표현이 의도치 않게 유사도 높게 나올 수 있다.

---

### 원칙 4 — 배치 업로드 JSON 작성 요령

이 POC의 일괄 업로드(`POST /api/v1/embeddings/batch`)에서 효과적인 데이터 형태:

```json
[
  {
    "id": "spring-001",
    "title": "Spring Boot 의존성 설정",
    "desc": "[Spring Boot] build.gradle에 spring-boot-starter-web을 추가하면 REST API 서버를 구성할 수 있습니다."
  },
  {
    "id": "spring-002",
    "title": "JWT 인증 구현",
    "desc": "[Spring Security] jjwt 라이브러리로 HS256 방식의 토큰을 발급하고 Authorization 헤더에서 검증하는 방법입니다."
  },
  {
    "id": "spring-003",
    "title": "MyBatis XML 매퍼 작성",
    "desc": "[MyBatis] SQL을 XML 파일에 작성하고 Mapper 인터페이스로 호출하는 방식. 어노테이션 방식보다 복잡한 동적 SQL에 적합합니다."
  }
]
```

**핵심 체크리스트**:

| 항목 | 권장 |
|------|------|
| `desc` 길이 | 1~3 문장 (50~200자) |
| 텍스트 형태 | 명사 나열 X → 자연어 문장 O |
| 도메인 맥락 | `[카테고리]` 접두사로 명시 |
| 의미 단위 | 하나의 항목에 하나의 개념만 |
| 중복 내용 | 같은 의미의 문서 여러 개 → 검색 결과가 한 주제로 쏠림 주의 |

---

### 요약

```
검색 품질 = 임베딩 텍스트 품질 × 모델 품질
```

모델을 바꾸는 것보다 **입력 텍스트를 자연어 문장으로 만들고 제목을 합치는 것**이 더 즉각적인 효과를 낸다.

---

## 모델·차원 변경 가이드

### 케이스 A — 모델만 교체 (차원 동일)

예: `text-embedding-3-small` → `text-embedding-ada-002` (둘 다 1536차원)

**환경변수 하나만 변경하면 된다.**

```
AZURE_OPENAI_DEPLOYMENT_NAME=새-배포-이름
```

소스 코드 수정 불필요. `OpenAiConfig`가 환경변수로 URL을 조합하고,  
`EmbeddingVector`는 API 응답 차원을 그대로 사용한다.

---

### 케이스 B — 차원이 바뀌는 경우

예: 1536 → 3072

**수정 파일 2개:**

| 파일 | 변경 내용 |
|------|----------|
| `src/main/resources/schema.sql` | `vector(1536)` → `vector(3072)` |
| `poc-deploy/init.sql` | `vector(1536)` → `vector(3072)` |

**기존 DB 컬럼 재생성 (SQL 직접 실행):**

```sql
-- schema.sql의 IF NOT EXISTS는 이미 존재하는 컬럼을 수정하지 않으므로
-- 기존 DB에는 직접 실행해야 한다
DROP INDEX documents_embedding_idx;
ALTER TABLE documents DROP COLUMN embedding;
ALTER TABLE documents ADD COLUMN embedding vector(3072);
CREATE INDEX documents_embedding_idx
    ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

> 기존 문서의 `embedding`이 모두 `NULL`이 되므로 **전체 재임베딩**이 필요하다.

**수정하지 않아도 되는 파일:**

| 파일 | 이유 |
|------|------|
| `VectorTypeHandler.java` | `float[]` → `PGvector` 변환만 함, 차원 무관 |
| `OpenAiEmbeddingService.java` | API 응답 차원을 그대로 사용, 하드코딩 없음 |
| `DocumentMapper.xml` | SQL에 차원 명시 없음 |
| `OpenAiConfig.java` | 환경변수로 주입 |

---

## 구현 핵심 포인트

### VectorTypeHandler

MyBatis와 pgvector 사이의 타입 변환 브리지.

```java
// 쓰기: float[] → PGvector → JDBC setObject (Types.OTHER)
ps.setObject(i, new PGvector(parameter.getValues()));

// 읽기: DB 문자열 "[0.1,-0.2,...]" → EmbeddingVector.parse()
EmbeddingVector.parse(rs.getString(columnName));
```

`application.yml`의 `type-handlers-package`에 패키지를 등록해야 자동 적용된다.

---

### MyBatis XML에서 <=> 연산자

XML에서 `<` 기호는 태그 시작으로 파싱되어 오류가 발생한다.  
반드시 `CDATA` 섹션으로 감싸야 한다.

```xml
<!-- 잘못된 방법 — XML 파싱 오류 -->
ORDER BY embedding <=> #{queryVector}

<!-- 올바른 방법 -->
ORDER BY embedding <![CDATA[ <=> ]]> #{queryVector}
```

---

### Azure OpenAI 인증 방식

Azure OpenAI는 일반 OpenAI API와 인증 헤더가 다르다.

```java
// Azure: api-key 헤더
headers.set("api-key", openAiConfig.getApiKey());

// 일반 OpenAI: Authorization 헤더 (이 프로젝트에서 사용하지 않음)
// headers.set("Authorization", "Bearer " + apiKey);
```

Request body에 `model` 필드가 없다. 모델은 URL의 배포 이름으로 지정된다.

```
GET {endpoint}/openai/deployments/{deployment-name}/embeddings?api-version={version}
```

---

### 예외 처리

`GlobalExceptionHandler` (`@RestControllerAdvice`):

| 예외 | HTTP 상태 | 용도 |
|------|----------|------|
| `IllegalArgumentException` | 401 | 인증 실패 (잘못된 JWT, 비밀번호 불일치) |
| `MethodArgumentNotValidException` | 400 | `@Valid` 유효성 검사 실패 |
| `RuntimeException` | 500 | 그 외 서버 오류 |

---

## 상용환경 적용 시 유의사항

### 보안

**JWT Secret Key**

현재 `application.yml`의 기본값(`poc-vector-search-jwt-secret-key-32ch!!`)은 절대 상용에서 사용하면 안 된다.  
256bit(32자) 이상의 랜덤 값을 생성해 Secrets Manager(AWS SSM, Azure Key Vault 등)로 주입한다.

```bash
# 안전한 시크릿 생성 예시
openssl rand -base64 32
```

**API Key 관리**

`AZURE_OPENAI_API_KEY`를 환경변수로만 관리하지 말고, 비밀 관리 서비스에 저장한다.  
로그·에러 응답·스택 트레이스에 API Key가 노출되지 않도록 주의한다.

**BCrypt 라운드 수**

현재 초기 데이터의 비밀번호는 `$2b$10$...` (10 라운드). 상용에서는 12 라운드 이상을 권장한다.  
라운드가 올라갈수록 로그인 응답 시간이 길어지므로 서버 사양에 맞게 조정한다.

**에러 응답 노출**

현재 `RuntimeException → 500` 핸들러가 `e.getMessage()`를 그대로 응답 body에 포함한다.  
상용에서는 내부 오류 메시지가 클라이언트에 노출되지 않도록 일반 메시지로 대체해야 한다.

```java
// 상용에서는 이렇게 변경
return ResponseEntity.status(500).body("서버 오류가 발생했습니다.");
```

**HTTPS**

모든 트래픽은 TLS 종료를 Nginx 또는 로드밸런서에서 처리한다.  
Spring Boot 자체에 TLS를 설정하는 경우 `server.ssl.*` 설정 필요.

---

---

### Azure OpenAI 사용량 제한

Azure OpenAI는 배포(Deployment)별로 **TPM(분당 토큰)** 과 **RPM(분당 요청)** 제한이 있다.

```
일반 검색 요청 1건 = 쿼리 텍스트를 임베딩 API 1회 호출
일괄 업로드 100건 = 임베딩 API 100회 순차 호출  ← rate limit 초과 위험
```

현재 `bulkCreate()`는 건별 순차 호출에 재시도(retry) 로직이 없다.  
상용에서는 아래를 반드시 추가한다:

- **Exponential Backoff Retry**: HTTP 429 응답 시 대기 후 재시도
- **일괄 처리 간격 조절**: 건당 호출 사이에 딜레이 삽입
- **배치 크기 제한**: 단일 요청으로 처리할 수 있는 최대 건수 제한

Azure OpenAI `text-embedding-3-small` 기본 할당량 예시:

| 항목 | 기본값 |
|------|--------|
| TPM | 모델/리전별 상이 (Azure 포털 확인) |
| RPM | TPM / 1000 × 6 |

---

### pgvector 인덱스 운영

**IVFFlat 인덱스 품질 저하**

IVFFlat은 인덱스 생성 시점의 데이터 분포를 기반으로 클러스터를 나눈다.  
이후 데이터가 대량으로 추가되면 클러스터 균형이 깨져 **검색 정확도(recall)가 떨어진다.**

```sql
-- 무중단 인덱스 재구성 (PostgreSQL 12+)
-- 일반 REINDEX는 테이블 전체에 락이 걸리므로 운영 중 금지
REINDEX INDEX CONCURRENTLY documents_embedding_idx;
```

데이터가 2배 이상 증가했거나 검색 품질이 체감될 때 실행을 권장한다.

**상용에서는 HNSW 인덱스 권장**

IVFFlat은 인덱스 생성 전에 데이터가 충분해야 하고 주기적 재구성이 필요하다.  
HNSW는 데이터 추가에 따라 그래프가 동적으로 갱신되어 재구성이 불필요하다.

```sql
-- 기존 IVFFlat 제거 후 HNSW로 교체
DROP INDEX CONCURRENTLY documents_embedding_idx;
CREATE INDEX CONCURRENTLY documents_embedding_idx
    ON documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
-- CONCURRENTLY: 인덱스 빌드 중 읽기/쓰기 계속 가능 (빌드 시간 더 걸림)
```

**인덱스 빌드 메모리 설정**

인덱스 빌드 속도는 `maintenance_work_mem`에 크게 영향받는다.  
세션 단위로 올려 빌드한 뒤 원복한다.

```sql
SET maintenance_work_mem = '1GB';
CREATE INDEX ...;
RESET maintenance_work_mem;
```

---

### 임베딩 데이터 일관성

**모델 버전 고정**

같은 배포 이름(`text-embedding-3-small`)이라도 Azure가 내부 모델 버전을 업데이트하면  
동일 텍스트의 임베딩 값이 달라질 수 있다.  
모델이 바뀌면 기존 임베딩과 신규 임베딩의 유사도 계산 결과가 신뢰할 수 없어진다.

> Azure OpenAI는 배포 시 모델 버전을 특정 버전으로 고정하는 옵션을 제공한다.  
> 상용에서는 반드시 버전을 고정하고, 변경 시 전체 재임베딩을 계획한다.

**서로 다른 모델의 임베딩 혼재 금지**

`documents.model` 컬럼에 모델명이 저장되지만, 현재 코드는 검색 시 이를 필터링하지 않는다.  
모델 A로 생성된 벡터와 모델 B로 생성된 벡터를 같은 테이블에서 함께 검색하면  
두 벡터 공간이 달라 의미 없는 결과가 나온다.

모델을 교체할 때는 기존 데이터를 모두 삭제하고 새 모델로 전체 재임베딩해야 한다.

**전체 재임베딩 절차 (다운타임 최소화)**

```
1. 신규 모델용 컬럼 추가 (embedding_v2 vector(차원))
2. 새 문서는 embedding_v2 에만 저장
3. 백그라운드 배치로 기존 문서 순차 재임베딩 → embedding_v2 채우기
4. 재임베딩 완료 후 검색 쿼리를 embedding_v2 기준으로 전환
5. 기존 embedding 컬럼 삭제
```

---

### 용량 계획

벡터 컬럼은 일반 텍스트보다 훨씬 많은 저장 공간을 사용한다.

```
1536차원 float32 벡터 1개 = 1536 × 4byte = 6,144 byte ≈ 6 KB
문서 10만 건              = 10만 × 6KB = 약 600 MB (벡터만)
HNSW 인덱스               = 벡터 데이터의 약 2~3배 메모리 상주
```

| 문서 수 | 벡터 데이터 크기 | HNSW 인덱스 메모리 |
|---------|----------------|------------------|
| 10만 건 | ~600 MB | ~1.2 ~ 1.8 GB |
| 100만 건 | ~6 GB | ~12 ~ 18 GB |

DB 서버의 `shared_buffers`와 `work_mem` 설정이 인덱스 성능에 직결된다.  
인덱스가 메모리에 올라오지 못하면 디스크 I/O로 폴백되어 검색 속도가 급격히 저하된다.

```sql
-- postgresql.conf 권장 설정 (메모리 16GB 기준 예시)
shared_buffers = 4GB         -- 전체 메모리의 25%
work_mem = 256MB             -- 정렬·해시 작업당 사용량
maintenance_work_mem = 1GB   -- 인덱스 빌드용
```

---

### DB 백업 및 복구

벡터 데이터는 원본 텍스트를 다시 임베딩하면 재생성할 수 있지만,  
대용량일 경우 재임베딩 비용(API 요금 + 시간)이 크다. 정기 백업을 반드시 설정한다.

```bash
# pg_dump로 전체 백업 (벡터 데이터 포함)
pg_dump -h localhost -U postgres poc_vector > backup.sql

# 복구
psql -h localhost -U postgres poc_vector < backup.sql
```

RDS/Cloud SQL 사용 시 자동 백업 및 포인트-인-타임 복구 설정을 활성화한다.

---

### 모니터링 지표

상용 운영 시 아래 지표를 Prometheus/Grafana 등으로 수집한다.

| 지표 | 설명 | 임계값 예시 |
|------|------|------------|
| 검색 응답 시간 | 임베딩 API + DB 검색 합산 | p99 < 2초 |
| Azure OpenAI 오류율 | 429(rate limit), 5xx | > 1% 알람 |
| DB 연결 풀 사용률 | HikariCP active/total | > 80% 알람 |
| `documents` 테이블 행 수 | 인덱스 재구성 시점 판단 | 2배 증가 시 REINDEX 검토 |
| 벡터 인덱스 크기 | `pg_relation_size()` | 메모리 용량 초과 여부 |

```sql
-- 인덱스 크기 확인
SELECT pg_size_pretty(pg_relation_size('documents_embedding_idx'));

-- 테이블 전체 크기 확인
SELECT pg_size_pretty(pg_total_relation_size('documents'));
```

---

### Java 1.8 관련 주의사항

**TLS 1.3 문제**

Java 1.8u292 이상에서 Azure OpenAI 등 일부 엔드포인트와 TLS 1.3 협상이 실패할 수 있다.  
현재 `JAVA_TOOL_OPTIONS`로 TLS 1.2를 강제해 회피하고 있다:

```
JAVA_TOOL_OPTIONS=-Dhttps.protocols=TLSv1.2 -Djdk.tls.client.protocols=TLSv1.2
```

**Java 버전 업그레이드 고려**

Java 1.8은 Oracle 기준 2030년까지 지원이지만, Spring Boot 3.x는 Java 17 이상을 요구한다.  
신규 기능(record, virtual thread, text block 등)과 보안 패치를 위해 Java 17 또는 21로  
마이그레이션을 장기 계획에 포함하는 것을 권장한다.
