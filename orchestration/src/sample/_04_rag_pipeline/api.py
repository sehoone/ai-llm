"""샘플 04 — RAG 파이프라인 API

Routes:
    POST /api/v1/sample/rag/upload  — 문서 업로드 (청킹 + 임베딩 + 벡터 저장)
    POST /api/v1/sample/rag/search  — 유사도 검색
    POST /api/v1/sample/rag/ask     — RAG 기반 Q&A (검색 + LLM 컨텍스트 주입)
    DELETE /api/v1/sample/rag/docs  — sample rag_key 문서 삭제

학습 포인트:
    1. rag_key로 챗봇/에이전트별 지식베이스를 격리
    2. 문서는 500자 청크로 분할 → text-embedding-3-small(1536차원)로 임베딩
    3. pgvector cosine similarity로 가장 유사한 청크 검색
    4. 검색된 청크를 system_prompt에 주입 → LLM이 문서 기반으로 답변

테스트 방법:
    1. POST /upload 로 문서 업로드
    2. POST /search 로 유사 청크 확인
    3. POST /ask 로 RAG 기반 Q&A 테스트
"""

import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, text

from src.chatbot.api.chatbot_api import agent
from src.chatbot.schemas.chat_schema import Message
from src.common.services.database import database_service
from src.rag.services.rag_service import RAGService

router = APIRouter()
rag_service = RAGService()

# 샘플 전용 rag_key (실제 프로젝트 데이터와 격리)
SAMPLE_RAG_KEY = "sample-demo"
SAMPLE_RAG_GROUP = "sample-group"
SAMPLE_RAG_TYPE = "chatbot_shared"


class SearchRequest(BaseModel):
    query: str
    rag_key: str = SAMPLE_RAG_KEY
    top_k: int = 3


class SearchResponse(BaseModel):
    results: list[dict]
    query: str
    rag_key: str


class AskRequest(BaseModel):
    question: str
    rag_key: str = SAMPLE_RAG_KEY
    session_id: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    rag_key: str
    session_id: str
    retrieved_chunks: int


@router.post(
    "/upload",
    summary="문서 업로드 (청킹 + 임베딩)",
    description="""
텍스트 파일을 업로드하면 RAG 파이프라인을 통해 처리합니다.

**처리 흐름:**
```
파일 텍스트 추출
    → 청킹 (500자 단위, 100자 overlap)
    → OpenAI text-embedding-3-small 임베딩 (1536차원)
    → PostgreSQL rag_embedding 테이블 (pgvector) 저장
```

**지원 형식:** text/plain, text/markdown, application/json, text/csv

**실제 구현 코드:** `src/rag/services/rag_service.py` `add_document_to_rag()`
    """,
)
async def upload_document(
    file: UploadFile = File(..., description="업로드할 텍스트 파일"),
    rag_key: str = Form(default=SAMPLE_RAG_KEY, description="지식베이스 식별 키"),
):
    allowed_types = {"text/plain", "text/markdown", "application/json", "text/csv"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {file.content_type}. 허용: {', '.join(allowed_types)}",
        )

    content_bytes = await file.read()
    if len(content_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="파일 크기는 10MB를 초과할 수 없습니다.")

    try:
        text_content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text_content = content_bytes.decode("utf-8", errors="replace")

    # doc_id=0: 샘플 전용 임시 ID (실제 프로젝트에서는 Document 레코드 생성 후 doc_id 사용)
    success = await rag_service.add_document_to_rag(
        doc_id=0,
        rag_key=rag_key,
        rag_group=SAMPLE_RAG_GROUP,
        rag_type=SAMPLE_RAG_TYPE,
        content=text_content,
    )

    if not success:
        raise HTTPException(status_code=500, detail="임베딩 저장에 실패했습니다.")

    chunks = rag_service._chunk_text(text_content)
    return {
        "message": "업로드 완료",
        "filename": file.filename,
        "rag_key": rag_key,
        "chunk_count": len(chunks),
        "char_count": len(text_content),
    }


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="유사도 검색",
    description="""
질문과 가장 유사한 문서 청크를 cosine similarity로 검색합니다.

**pgvector 검색:**
```sql
SELECT content, 1 - (embedding <=> query_vector) AS similarity
FROM rag_embedding
WHERE rag_key = :rag_key
ORDER BY embedding <=> query_vector
LIMIT :limit
```

**실제 구현 코드:** `src/rag/services/rag_service.py` `search_rag()`
    """,
)
async def search_documents(body: SearchRequest):
    results = await rag_service.search_rag(
        rag_key=body.rag_key,
        rag_type=SAMPLE_RAG_TYPE,
        query=body.query,
        limit=body.top_k,
    )
    return SearchResponse(
        results=results,
        query=body.query,
        rag_key=body.rag_key,
    )


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="RAG 기반 Q&A",
    description="""
문서 검색 결과를 컨텍스트로 주입하고 LangGraphAgent로 답변합니다.

**흐름:**
```
1. rag_key → pgvector 유사도 검색
2. 검색된 청크 → system_prompt에 "참고 문서:" 형태로 주입
3. LangGraphAgent.get_response(rag_key=...) 호출
```

**LangGraphAgent의 RAG 처리 방식:**
`rag_key`를 GraphState에 전달하면 `_chat` 노드에서
`augment_prompt_with_rag()`를 호출하여 자동으로 컨텍스트를 주입합니다.

**실제 구현 코드:** `src/agent/api/agent_api.py`, `src/rag/services/rag_service.py`
    """,
)
async def ask_with_rag(body: AskRequest):
    session_id = body.session_id or str(uuid.uuid4())

    retrieved = await rag_service.search_rag(
        rag_key=body.rag_key,
        rag_type=SAMPLE_RAG_TYPE,
        query=body.question,
        limit=3,
    )

    messages = [Message(role="user", content=body.question)]
    result = await agent.get_response(
        messages=messages,
        session_id=session_id,
        rag_key=body.rag_key,
    )

    last_assistant = next(
        (m for m in reversed(result) if m.role == "assistant"), None
    )
    if not last_assistant:
        raise HTTPException(status_code=500, detail="에이전트 응답을 받지 못했습니다.")

    return AskResponse(
        answer=last_assistant.content,
        rag_key=body.rag_key,
        session_id=session_id,
        retrieved_chunks=len(retrieved),
    )


@router.delete(
    "/docs",
    summary="샘플 문서 삭제",
    description=f"rag_key로 저장된 샘플 임베딩(doc_id=0)을 모두 삭제합니다.",
)
async def delete_sample_docs(rag_key: str = SAMPLE_RAG_KEY):
    with Session(database_service.engine) as session:
        result = session.exec(
            text("DELETE FROM rag_embedding WHERE rag_key = :rag_key AND doc_id = 0")
            .bindparams(rag_key=rag_key)
        )
        session.commit()
        deleted = result.rowcount

    return {"message": "삭제 완료", "rag_key": rag_key, "deleted_count": deleted}
