# Multi-Bot RAG System Documentation

## Overview

The RAG (Retrieval-Augmented Generation) system has been enhanced to support multiple chatbots, each with their own isolated knowledge bases. This allows different chatbots to maintain separate document libraries and conduct independent semantic searches.

## Architecture

### Key Components

#### 1. Document Model (`app/models/document.py`)
- Added `rag_key` field to identify which chatbot/RAG this document belongs to
- Indexed on `rag_key` for efficient filtering
- Each document is associated with a user and a specific RAG

```python
class Document(BaseModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    rag_key: str = Field(index=True)  # NEW: Chatbot identifier
    filename: str
    content: str
    doc_metadata: Optional[str]
    created_at: datetime
    updated_at: datetime
```

#### 2. RAG Embedding Table (`rag_embedding`)
- Stores vector embeddings for document chunks
- Includes `rag_key` field for isolation
- Indexed on `rag_key` for fast RAG-specific searches

```sql
CREATE TABLE rag_embedding (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    rag_key VARCHAR(255) NOT NULL,          -- NEW: Chatbot identifier
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_rag_embedding_rag_key ON rag_embedding(rag_key);
```

#### 3. RAG Service (`app/services/rag.py`)
Updated methods to handle `rag_key`:

```python
async def add_document_to_rag(
    self, 
    doc_id: int, 
    rag_key: str,          # NEW: Specify which chatbot
    content: str
) -> bool:
    """Add document with embeddings to specific RAG"""

async def search_rag(
    self, 
    user_id: int, 
    rag_key: str,          # NEW: Search specific RAG
    query: str, 
    limit: int = 5
) -> List[dict]:
    """Search within specific chatbot's knowledge base"""

async def augment_prompt_with_rag(
    self, 
    user_id: int, 
    rag_key: str,          # NEW: Use specific RAG
    message: str, 
    limit: int = 3
) -> str:
    """Augment prompt with context from specific RAG"""
```

#### 4. Document Service (`app/services/document.py`)
Updated to support `rag_key`:

```python
async def create_document(
    self, 
    user_id: int, 
    rag_key: str,          # NEW: Chatbot identifier
    filename: str, 
    content: str, 
    doc_metadata: Optional[dict]
) -> Document:
    """Create document for specific chatbot"""

async def get_user_documents(
    self, 
    user_id: int, 
    rag_key: Optional[str] = None  # NEW: Optional filter
) -> List[Document]:
    """Get documents, optionally filtered by RAG key"""
```

#### 5. RAG API Endpoints (`app/api/v1/rag.py`)
All endpoints now require or accept `rag_key`:

```python
@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile,
    rag_key: str = Form(...),       # NEW: Required
    tags: str = Form(default=""),
    user: User = Depends(get_current_user)
):
    """Upload to specific chatbot RAG"""

@router.get("/documents")
async def get_user_documents(
    request: Request,
    rag_key: str = None,            # NEW: Optional filter
    user: User = Depends(get_current_user)
):
    """Get documents, optionally filtered by RAG key"""

@router.post("/search")
async def search_rag(
    request: Request,
    rag_key: str = Form(...),       # NEW: Required
    query: str = Form(...),
    limit: int = Form(default=5),
    user: User = Depends(get_current_user)
):
    """Search specific RAG"""
```

## Usage Examples

### 1. Upload Document for Specific Chatbot

```bash
# Upload to "chatbot_general" RAG
curl -X POST http://localhost:8000/api/v1/rag/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@guide.txt" \
  -F "rag_key=chatbot_general" \
  -F "tags=important"
```

### 2. List Documents by RAG Key

```bash
# Get all documents for current user
curl -X GET http://localhost:8000/api/v1/rag/documents \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get only documents for "chatbot_support" RAG
curl -X GET "http://localhost:8000/api/v1/rag/documents?rag_key=chatbot_support" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Search Specific RAG

```bash
# Search in "chatbot_sales" RAG
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "rag_key=chatbot_sales&query=pricing&limit=5"
```

### 4. Python Integration

```python
from app.services.rag import rag_service

# Add document to specific RAG
success = await rag_service.add_document_to_rag(
    doc_id=123,
    rag_key="chatbot_support",
    content="How to reset password..."
)

# Search specific RAG
results = await rag_service.search_rag(
    user_id=1,
    rag_key="chatbot_general",
    query="What is Python?",
    limit=3
)

# Augment prompt with context from specific RAG
augmented = await rag_service.augment_prompt_with_rag(
    user_id=1,
    rag_key="chatbot_sales",
    message="Tell me about your pricing",
    limit=3
)
```

## Chatbot Integration (Next Steps)

### In `app/api/v1/chatbot.py`

```python
from app.services.rag import rag_service

@router.post("/chat")
async def chat_with_bot(
    request: Request,
    request_data: ChatRequest,
    rag_key: str = Query(...),  # Add this to specify which bot
    user: User = Depends(get_current_user),
):
    """Chat with specific chatbot using its RAG"""
    
    # Augment user message with RAG context
    augmented_message = await rag_service.augment_prompt_with_rag(
        user_id=user.id,
        rag_key=rag_key,
        message=request_data.message,
        limit=3
    )
    
    # Continue with LLM agent using augmented message
    # ...
```

### Example Chatbot Definitions

```python
CHATBOTS = {
    "chatbot_general": {
        "name": "General Assistant",
        "description": "General-purpose assistant",
        "system_prompt": "You are a helpful general assistant..."
    },
    "chatbot_support": {
        "name": "Support Agent",
        "description": "Customer support specialist",
        "system_prompt": "You are a customer support specialist..."
    },
    "chatbot_sales": {
        "name": "Sales Agent",
        "description": "Sales specialist",
        "system_prompt": "You are a sales specialist..."
    }
}
```

## Data Flow Diagram

```
User Request
    ↓
API Endpoint (includes rag_key)
    ↓
Service Layer
    ├─→ Document Service (filters by rag_key)
    ├─→ RAG Service (uses rag_key for embeddings)
    └─→ Database Layer
        ├─→ Document Table (WHERE rag_key = ?)
        └─→ RAG Embedding Table (WHERE rag_key = ?)
    ↓
Response (isolated to specific RAG)
```

## Benefits

### 1. **Knowledge Base Isolation**
- Each chatbot has completely separate documents
- No cross-contamination between bots
- Scalable to many chatbots

### 2. **User Efficiency**
- Single user can manage documents for multiple bots
- Easy filtering by chatbot type
- Organized knowledge management

### 3. **Performance**
- Indexed searches on `rag_key`
- Fast filtering in large datasets
- Efficient vector operations per RAG

### 4. **Security**
- Documents are still user-scoped
- Cannot access other users' documents
- RAG key prevents unauthorized access

### 5. **Flexibility**
- Easy to add new chatbots
- No schema changes required
- Documents can be shared via different RAG keys if needed

## Testing

### Run Test Script

```bash
$env:APP_ENV='development'; uv run python test_rag.py
```

The test demonstrates:
- ✅ Multiple RAG key uploads
- ✅ Document isolation by RAG key
- ✅ Filtering documents by RAG key
- ✅ Searching specific RAGs
- ✅ Cross-RAG isolation verification

### Manual Testing

```bash
# 1. Register and get token
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Use returned access_token in subsequent requests

# 2. Upload for different RAGs
curl -X POST http://localhost:8000/api/v1/rag/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@doc1.txt" \
  -F "rag_key=chatbot_general"

curl -X POST http://localhost:8000/api/v1/rag/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@doc2.txt" \
  -F "rag_key=chatbot_support"

# 3. Verify isolation
curl -X GET "http://localhost:8000/api/v1/rag/documents?rag_key=chatbot_general" \
  -H "Authorization: Bearer $TOKEN"

curl -X GET "http://localhost:8000/api/v1/rag/documents?rag_key=chatbot_support" \
  -H "Authorization: Bearer $TOKEN"
```

## Migration Notes

### For Existing Deployments

If you have existing RAG documents without a `rag_key`, you need to:

1. Add a migration script to backfill `rag_key` for existing documents
2. Example migration:

```sql
-- Set default rag_key for existing documents
UPDATE document 
SET rag_key = 'default_chatbot' 
WHERE rag_key IS NULL;

-- If you need to split documents into different RAGs
UPDATE document 
SET rag_key = 'chatbot_support' 
WHERE doc_metadata LIKE '%support%';
```

3. Re-generate embeddings for updated documents (if needed)

## Future Enhancements

1. **Chatbot Management API**
   - Create/update/delete chatbot definitions
   - Manage RAG key mappings
   - Configure bot-specific settings

2. **Advanced Search**
   - Hybrid search (text + vector)
   - Multi-document relevance scoring
   - Cross-RAG search with weighting

3. **Document Organization**
   - Folder/category structure per RAG
   - Document versioning
   - Batch operations (upload/delete/move)

4. **Analytics**
   - Search analytics per RAG
   - Most-used documents
   - Performance metrics

5. **Sharing**
   - Share documents between users
   - Role-based access control
   - Document versioning with history
