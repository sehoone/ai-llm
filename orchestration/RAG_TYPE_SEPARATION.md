# RAG 데이터 타입 분리 - 사용자별 vs 챗봇별

## 개요

RAG 시스템이 두 가지 타입으로 분리되었습니다:
- **user_isolated**: 사용자별로 격리된 RAG (같은 사용자만 접근)
- **chatbot_shared**: 챗봇별로 공유되는 글로벌 RAG (모든 사용자 접근)

## 데이터 구조

### Document 테이블

```sql
CREATE TABLE document (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id) NULLABLE,  -- NULL for chatbot_shared
    rag_key VARCHAR(255) NOT NULL,                   -- 챗봇 식별자
    rag_type VARCHAR(50) NOT NULL,                   -- 'user_isolated' or 'chatbot_shared'
    filename VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    doc_metadata VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_document_user_rag ON document(user_id, rag_key, rag_type);
```

### RAG Embedding 테이블

```sql
CREATE TABLE rag_embedding (
    id INTEGER PRIMARY KEY,
    doc_id INTEGER REFERENCES document(id) ON DELETE CASCADE,
    rag_key VARCHAR(255) NOT NULL,
    rag_type VARCHAR(50) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_rag_embedding_rag_key_type ON rag_embedding(rag_key, rag_type);
```

## 사용 패턴

### 1. User-Isolated RAG (사용자별 격리)

**용도:** 개별 사용자의 개인 문서 저장소
- 사용자가 업로드한 문서
- 사용자 전용 정보
- 회사/조직별 기밀 문서

**업로드:**
```bash
curl -X POST http://localhost:8000/api/v1/rag/upload \
  -H "Authorization: Bearer USER_TOKEN" \
  -F "file=@my_document.txt" \
  -F "rag_key=chatbot_support" \
  -F "rag_type=user_isolated"    # 사용자별 격리
```

**데이터 흐름:**
```
User1 uploads doc          User2 cannot access
       ↓
Document(user_id=1, rag_type="user_isolated")
       ↓
RAG Search Query:
  - user_id = 1 (필수)
  - rag_key = "chatbot_support"
  - rag_type = "user_isolated"
       ↓
Only User1's documents returned
```

### 2. Chatbot-Shared RAG (챗봇별 공유)

**용도:** 모든 사용자가 공유하는 글로벌 지식 베이스
- 회사 정책 문서
- 제품 매뉴얼
- FAQ 및 일반 정보
- 법률/준수 문서

**업로드:**
```bash
# 관리자가 글로벌 문서 업로드
curl -X POST http://localhost:8000/api/v1/rag/upload \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -F "file=@company_policy.txt" \
  -F "rag_key=chatbot_general" \
  -F "rag_type=chatbot_shared"   # 글로벌 공유
```

**데이터 구조:**
```
Document(user_id=null, rag_type="chatbot_shared")
       ↓
All users can search and access
```

**검색:**
```bash
# User1 검색
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Authorization: Bearer USER1_TOKEN" \
  -d "rag_key=chatbot_general&rag_type=chatbot_shared&query=policy&limit=5"

# User2 검색 - 같은 결과
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Authorization: Bearer USER2_TOKEN" \
  -d "rag_key=chatbot_general&rag_type=chatbot_shared&query=policy&limit=5"
```

## 비교표

| 항목 | user_isolated | chatbot_shared |
|------|---------------|----------------|
| **데이터 소유** | 개별 사용자 | 글로벌 공유 |
| **user_id** | 필수 (각 사용자) | NULL (공유) |
| **접근 제어** | 본인만 | 모든 사용자 |
| **검색 필터** | WHERE user_id = ? | WHERE user_id IS NULL |
| **사용 사례** | 개인 문서, 개인화 | 공개 정보, 정책 |
| **권한** | 자동 (본인) | 필요시 관리자 관리 |

## Python 서비스 사용

### RAG Service

```python
from app.services.rag import rag_service

# 1. User-Isolated RAG에 문서 추가
await rag_service.add_document_to_rag(
    doc_id=123,
    rag_key="chatbot_support",
    rag_type="user_isolated",
    content="개인 문서 내용..."
)

# 2. Chatbot-Shared RAG에 문서 추가
await rag_service.add_document_to_rag(
    doc_id=456,
    rag_key="chatbot_general",
    rag_type="chatbot_shared",
    content="글로벌 정책..."
)

# 3. User-Isolated 검색
results = await rag_service.search_rag(
    rag_key="chatbot_support",
    rag_type="user_isolated",
    user_id=1,  # 필수
    query="기술 지원",
    limit=5
)

# 4. Chatbot-Shared 검색
results = await rag_service.search_rag(
    rag_key="chatbot_general",
    rag_type="chatbot_shared",
    user_id=None,  # 사용 안 함
    query="회사 정책",
    limit=5
)

# 5. 프롬프트 확장 (User-Isolated)
augmented = await rag_service.augment_prompt_with_rag(
    rag_key="chatbot_support",
    rag_type="user_isolated",
    user_id=1,
    message="기술 문제 해결 방법"
)

# 6. 프롬프트 확장 (Chatbot-Shared)
augmented = await rag_service.augment_prompt_with_rag(
    rag_key="chatbot_general",
    rag_type="chatbot_shared",
    user_id=None,
    message="회사의 반환 정책은?"
)
```

### Document Service

```python
from app.services.document import document_service

# 1. User-Isolated 문서 생성
doc = await document_service.create_document(
    rag_key="chatbot_support",
    rag_type="user_isolated",
    filename="my_docs.txt",
    content="...",
    user_id=1,  # 필수
    doc_metadata={"tags": "중요"}
)

# 2. Chatbot-Shared 문서 생성
doc = await document_service.create_document(
    rag_key="chatbot_general",
    rag_type="chatbot_shared",
    filename="policy.txt",
    content="...",
    user_id=None,  # 공유 문서
    doc_metadata={"tags": "정책"}
)

# 3. 사용자의 모든 문서 조회
docs = await document_service.get_user_documents(
    user_id=1
)

# 4. 특정 RAG의 사용자 문서만 조회
docs = await document_service.get_user_documents(
    user_id=1,
    rag_key="chatbot_support",
    rag_type="user_isolated"
)
```

## 챗봇 통합 예시

```python
# app/api/v1/chatbot.py
@router.post("/chat")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    rag_key: str = Query(...),
    rag_type: str = Query(default="user_isolated"),  # 기본값
    user: User = Depends(get_current_user)
):
    """
    rag_type을 지정하여 다양한 RAG 데이터 사용
    
    Examples:
    - /chat?rag_key=chatbot_support&rag_type=user_isolated
      → 사용자 개인 문서 + 글로벌 정책
    
    - /chat?rag_key=chatbot_general&rag_type=chatbot_shared
      → 회사 정책만 사용
    """
    
    # User-Isolated RAG 검색 (사용자 개인 문서)
    user_docs = await rag_service.augment_prompt_with_rag(
        rag_key=rag_key,
        rag_type="user_isolated",
        user_id=user.id,
        message=chat_request.message,
        limit=3
    )
    
    # Chatbot-Shared RAG 검색 (글로벌 문서)
    shared_docs = await rag_service.augment_prompt_with_rag(
        rag_key=rag_key,
        rag_type="chatbot_shared",
        user_id=None,
        message=chat_request.message,
        limit=3
    )
    
    # 컨텍스트 조합
    combined_context = f"""
    개인 문서:
    {user_docs}
    
    회사 정책:
    {shared_docs}
    """
    
    # LLM에 전달하여 응답 생성
    response = await llm_service.call(
        message=chat_request.message,
        context=combined_context
    )
    
    return {"response": response}
```

## 마이그레이션 가이드

### 기존 데이터 마이그레이션

```sql
-- 1. 기존 user_isolated 문서
UPDATE document 
SET rag_type = 'user_isolated' 
WHERE user_id IS NOT NULL AND rag_type IS NULL;

-- 2. 기존 chatbot_shared 문서
UPDATE document 
SET rag_type = 'chatbot_shared', 
    user_id = NULL 
WHERE user_id IS NOT NULL AND rag_type = 'chatbot_shared';

-- 3. RAG embedding 테이블도 함께 업데이트
UPDATE rag_embedding 
SET rag_type = d.rag_type
FROM document d
WHERE rag_embedding.doc_id = d.id;
```

## 검색 로직

### User-Isolated 검색

```python
# SQL 쿼리
SELECT re.id, re.content, 1 - (re.embedding <=> query_vector) as similarity
FROM rag_embedding re
JOIN document d ON re.doc_id = d.id
WHERE d.user_id = :user_id           # ← 사용자 격리
  AND re.rag_key = :rag_key
  AND re.rag_type = 'user_isolated'
ORDER BY similarity DESC
LIMIT :limit
```

### Chatbot-Shared 검색

```python
# SQL 쿼리
SELECT re.id, re.content, 1 - (re.embedding <=> query_vector) as similarity
FROM rag_embedding re
JOIN document d ON re.doc_id = d.id
WHERE d.user_id IS NULL              # ← 글로벌 (user_id 없음)
  AND re.rag_key = :rag_key
  AND re.rag_type = 'chatbot_shared'
ORDER BY similarity DESC
LIMIT :limit
```

## 보안 고려사항

1. **User-Isolated RAG**
   - ✅ 각 사용자는 자신의 문서만 조회 가능
   - ✅ 다른 사용자의 문서 접근 불가
   - ✅ 데이터베이스 레벨에서 격리됨

2. **Chatbot-Shared RAG**
   - ✅ 관리자만 업로드 권한 (별도 권한 설정 필요)
   - ✅ 모든 사용자에게 공개
   - ✅ 민감한 정보는 포함하지 말 것

## API 엔드포인트

### 문서 업로드

```bash
POST /api/v1/rag/upload
Content-Type: multipart/form-data

file: document.txt
rag_key: chatbot_support
rag_type: user_isolated (또는 chatbot_shared)
tags: optional
```

### 문서 검색

```bash
POST /api/v1/rag/search
Content-Type: application/x-www-form-urlencoded

rag_key: chatbot_support
rag_type: user_isolated (또는 chatbot_shared)
query: 검색 쿼리
limit: 5
```

### 문서 목록

```bash
GET /api/v1/rag/documents?rag_key=chatbot_support&rag_type=user_isolated
Authorization: Bearer TOKEN
```

## 성능 최적화

### 인덱스 전략

```sql
-- Composite index for user-isolated searches
CREATE INDEX idx_rag_embedding_user_isolated 
ON rag_embedding(rag_key, rag_type) 
WHERE rag_type = 'user_isolated';

-- For shared documents
CREATE INDEX idx_rag_embedding_chatbot_shared 
ON rag_embedding(rag_key, rag_type) 
WHERE rag_type = 'chatbot_shared';

-- Vector index for similarity search
CREATE INDEX idx_rag_embedding_vector 
ON rag_embedding USING ivfflat (embedding vector_cosine_ops);
```

### 캐싱 전략

- Chatbot-Shared RAG 결과는 캐싱 가능
- User-Isolated RAG는 사용자별로 캐싱
- TTL: 1시간 (정책 변경 시 수동 갱신)
