# Multi-Bot RAG System - Changes Summary

## 📋 Overview
The RAG (Retrieval-Augmented Generation) system has been completely refactored to support multiple chatbots with isolated knowledge bases. Each chatbot can maintain its own document library and perform independent semantic searches using its `rag_key` as an identifier.

## 📝 Files Modified

### 1. **app/models/document.py**
**Changes:**
- Added `rag_key: str = Field(index=True)` field to Document model
- Allows each document to be associated with a specific chatbot

**Impact:**
- Documents now belong to specific chatbots identified by `rag_key`
- Enables efficient filtering and isolation of knowledge bases

### 2. **app/services/rag.py**
**Changes:**
- Updated `_get_embeddings()` method: Now uses singleton pattern with lazy initialization
- Added `_chunk_text()` method: Splits documents into 500-char chunks with 100-char overlap
- Modified `add_document_to_rag(doc_id, rag_key, content)`: 
  - Added `rag_key` parameter
  - Implements batch embedding processing (5 chunks per batch)
  - Stores `rag_key` in `rag_embedding` table for isolation
- Modified `search_rag(user_id, rag_key, query, limit)`:
  - Added `rag_key` parameter to WHERE clause
  - Only searches documents belonging to specific RAG
- Modified `augment_prompt_with_rag(user_id, rag_key, message, limit)`:
  - Added `rag_key` parameter for context retrieval

**Impact:**
- RAG operations now respect chatbot isolation
- Each chatbot can only search its own documents
- Efficient batch processing reduces API calls

### 3. **app/services/document.py**
**Changes:**
- Modified `create_document()`: Added `rag_key` parameter
- Modified `get_user_documents()`: Added optional `rag_key` filter parameter

**Impact:**
- Documents can be filtered by RAG key
- Users can manage documents for different chatbots

### 4. **app/api/v1/rag.py**
**Changes:**
- `POST /upload`: Added required `rag_key` form parameter
- `GET /documents`: Added optional `rag_key` query parameter for filtering
- `POST /search`: Added required `rag_key` form parameter
- All endpoints now pass `rag_key` to service layer

**Impact:**
- API clearly exposes chatbot separation
- Rate limiting applies per endpoint regardless of `rag_key`
- Users can manage documents for multiple chatbots

### 5. **README.md**
**Changes:**
- Added "Multi-Bot RAG System" section to features
- Added RAG endpoints to API Reference
- Added complete RAG system documentation with:
  - Architecture overview
  - Database schema
  - Usage examples (Python, cURL)
  - Testing instructions
- Updated project structure to include new files

**Impact:**
- Clear documentation of multi-bot capabilities
- Easy reference for API consumers
- Examples for integration

### 6. **MULTI_BOT_RAG.md** (NEW)
**Creates:**
- Comprehensive documentation of multi-bot RAG system
- Architecture details and components
- Detailed usage examples
- Integration guide for chatbot endpoints
- Data flow diagrams
- Benefits analysis
- Testing procedures
- Migration guide for existing deployments
- Future enhancement suggestions

**Impact:**
- Single source of truth for RAG architecture
- Facilitates team understanding and onboarding
- Provides roadmap for future development

### 7. **test_rag.py** (UPDATED)
**Changes:**
- Complete rewrite for multi-bot testing
- Tests three different RAG keys: `chatbot_general`, `chatbot_support`, `chatbot_sales`
- Demonstrates:
  - Uploading documents to different RAGs
  - Filtering documents by RAG key
  - Searching specific RAGs
  - Cross-RAG isolation verification
- Includes comprehensive output and step-by-step progress

**Impact:**
- Can verify multi-bot functionality end-to-end
- Validates RAG key isolation
- Demonstrates proper API usage

## 🗄️ Database Schema Changes

### New `rag_embedding` Table Structure

```sql
CREATE TABLE rag_embedding (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    rag_key VARCHAR(255) NOT NULL,              -- NEW
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rag_embedding_doc_id ON rag_embedding(doc_id);
CREATE INDEX idx_rag_embedding_rag_key ON rag_embedding(rag_key);  -- NEW
CREATE INDEX idx_rag_embedding_vector ON rag_embedding 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);
```

### Document Table Changes

```sql
-- NEW rag_key field added:
ALTER TABLE document ADD COLUMN rag_key VARCHAR(255) NOT NULL DEFAULT 'default';
CREATE INDEX idx_document_rag_key ON document(rag_key);
```

## 🔄 Data Flow Changes

### Before (Single RAG)
```
Upload → Document → Chunks → Embeddings → DB (no isolation)
Search → Query Embedding → Search All Embeddings → Results
```

### After (Multi-Bot RAG)
```
Upload + rag_key → Document(rag_key) → Chunks → Embeddings(rag_key) → DB
Search + rag_key → Query Embedding → Search Embeddings WHERE rag_key → Results
```

## 🚀 API Changes

### Upload Endpoint
**Before:**
```
POST /api/v1/rag/upload
Form: file, tags
```

**After:**
```
POST /api/v1/rag/upload
Form: file, rag_key (REQUIRED), tags
```

### Search Endpoint
**Before:**
```
POST /api/v1/rag/search
Form: query, limit
```

**After:**
```
POST /api/v1/rag/search
Form: rag_key (REQUIRED), query, limit
```

### List Documents Endpoint
**Before:**
```
GET /api/v1/rag/documents
Query: (none)
```

**After:**
```
GET /api/v1/rag/documents
Query: rag_key (optional filter)
```

## ✅ Backward Compatibility

### Breaking Changes
- ❌ `POST /rag/upload` now requires `rag_key` parameter
- ❌ `POST /rag/search` now requires `rag_key` parameter
- ❌ Documents without `rag_key` won't be searchable

### Migration Required
For existing documents, run:
```sql
UPDATE document SET rag_key = 'default' WHERE rag_key IS NULL;
```

## 🎯 Key Benefits

### 1. **Scalability**
- Support unlimited chatbots with single infrastructure
- Each bot has isolated knowledge base
- Linear scaling with number of bots

### 2. **Performance**
- Indexed searches on `rag_key`
- Batch embedding processing
- Rate limit protection between batches

### 3. **Security**
- User-scoped access maintained
- Chatbot isolation prevents data leakage
- Documents still require authentication

### 4. **Maintainability**
- Clear separation of concerns
- Easier to test each chatbot's RAG
- Simple to add new chatbots

### 5. **User Experience**
- Single user can manage multiple chatbots
- Clear document organization
- Easy chatbot-specific search

## 🧪 Testing Checklist

- [x] Document model accepts `rag_key`
- [x] RAG service uses `rag_key` for isolation
- [x] API endpoints require/accept `rag_key`
- [x] Database migrations handle new fields
- [x] Embedding generation works with new schema
- [x] Search respects `rag_key` boundaries
- [x] Test script validates multi-bot functionality
- [x] Documentation updated

## 🔮 Next Steps for Chatbot Integration

### 1. Update Chatbot Endpoint
```python
@router.post("/chat")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    rag_key: str = Query(...),
    user: User = Depends(get_current_user)
):
    # Pass rag_key to RAG service
    augmented_prompt = await rag_service.augment_prompt_with_rag(
        user_id=user.id,
        rag_key=rag_key,
        message=chat_request.message
    )
    # Use augmented_prompt with LLM agent
```

### 2. Create Chatbot Configuration
```python
AVAILABLE_BOTS = {
    "general": {"name": "General Assistant", "rag_key": "chatbot_general"},
    "support": {"name": "Support Bot", "rag_key": "chatbot_support"},
    "sales": {"name": "Sales Bot", "rag_key": "chatbot_sales"}
}
```

### 3. Add Bot Selection to Frontend
- Allow users to select which chatbot to talk to
- Each bot has its own chat history (optional)
- Each bot has its own RAG knowledge base

## 📊 Performance Metrics

### Document Chunking
- Chunk size: 500 characters
- Overlap: 100 characters
- Typical document breakdown:
  - 5KB file → ~10 chunks
  - 50KB file → ~100 chunks
  - 500KB file → ~1000 chunks

### Embedding Processing
- Batch size: 5 chunks per batch
- Delay between batches: 0.5 seconds
- Dimension: 1536 (OpenAI text-embedding-3-small)
- Typical API cost:
  - 1 document (5KB) → ~$0.00001
  - 100 documents (5KB each) → ~$0.001

### Search Performance
- Index: IVFFlat with 100 lists
- Expected query time: <100ms for 10K embeddings
- Scales efficiently with database growth

## 📚 Documentation

### Primary Documentation
- `README.md` - Project overview and quick start
- `MULTI_BOT_RAG.md` - Comprehensive RAG system documentation
- This file (`CHANGES.md`) - Summary of changes

### Code Documentation
- Docstrings in service classes
- Type hints on all methods
- Comments for complex logic

### API Documentation
- Swagger UI at `/docs`
- OpenAPI schema at `/openapi.json`
- ReDoc at `/redoc`

## 🔧 Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Document Model | ✅ Complete | rag_key field added |
| RAG Service | ✅ Complete | Multi-bot support |
| Document Service | ✅ Complete | RAG key filtering |
| RAG API Endpoints | ✅ Complete | rag_key parameters |
| Database Schema | ✅ Complete | rag_key indexed |
| Documentation | ✅ Complete | Comprehensive docs |
| Test Suite | ✅ Complete | Multi-bot test script |
| Chatbot Integration | ⏳ Pending | Ready for integration |
| Bot Configuration | ⏳ Pending | Ready for setup |
| Frontend Support | ⏳ Pending | Ready for UI |

---

**Last Updated:** November 30, 2025
**Status:** Ready for Integration Testing
