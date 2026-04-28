"""샘플 04: RAG (Retrieval-Augmented Generation) 파이프라인

실제 구현: src/rag/services/rag_service.py, src/rag/services/document_service.py

핵심 개념:
- RAG: LLM이 모르는 도메인 지식을 문서로 제공하는 기법
- 파이프라인: 문서 업로드 → 청킹 → 임베딩 → pgvector 저장 → 유사도 검색 → 컨텍스트 주입

단계별 설명:
1. 청킹(Chunking): 긴 문서를 작은 조각으로 분할
   - 이유: LLM의 컨텍스트 크기 제한 + 더 정밀한 유사도 검색
   - 파라미터: chunk_size=500자, overlap=100자 (경계에서 내용 손실 방지)

2. 임베딩(Embedding): 텍스트를 벡터(숫자 배열)로 변환
   - text-embedding-3-small: 1536차원 벡터
   - 의미적으로 유사한 텍스트 → 유사한 벡터

3. 벡터 저장(pgvector): PostgreSQL에 벡터 인덱스로 저장
   - cosine similarity로 가장 유사한 청크 검색
   - ivfflat 인덱스: 근사 최근접 이웃(ANN) 검색으로 대규모 벡터에서 빠른 검색

4. 검색 및 주입: 사용자 질문과 가장 유사한 청크를 찾아 system_prompt에 추가
"""

import textwrap
from typing import List, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, text


# ── 데이터 모델 ────────────────────────────────────────────────────────────────

class DocumentChunk(SQLModel, table=True):
    """RAG 임베딩 저장 테이블.

    실제 코드(src/rag/models/rag_embedding_model.py)에서는
    rag_key, user_id, document_id 등 추가 필드가 있음.
    """

    __tablename__ = "sample_rag_embedding"

    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(description="청크 원문")
    source: str = Field(description="문서 출처")
    rag_key: str = Field(description="격리 키 — 챗봇별 지식베이스 구분")
    # pgvector: 1536차원 float 배열 (text-embedding-3-small)
    embedding: List[float] = Field(
        sa_column=Column(Vector(1536)),
        description="임베딩 벡터",
    )


# ── 청킹 유틸리티 ──────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """텍스트를 고정 크기 + overlap 방식으로 청킹.

    overlap(겹침)이 필요한 이유:
    - 문단/문장이 청크 경계에서 잘릴 수 있음
    - 경계 부근의 내용이 두 청크 모두에 포함되면 검색 누락 방지

    실제 코드(src/rag/services/rag_service.py)에서는
    LangChain의 RecursiveCharacterTextSplitter 사용.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap  # overlap만큼 뒤로 이동

        # 마지막 청크 처리
        if start >= len(text):
            break

    return [c for c in chunks if c.strip()]


# ── RAG 서비스 ─────────────────────────────────────────────────────────────────

class SimpleRAGPipeline:
    """문서 업로드 → 검색 → 컨텍스트 주입을 담당하는 RAG 파이프라인."""

    def __init__(self, db_url: str, openai_api_key: str):
        self.engine = create_engine(db_url)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",  # 1536차원
            api_key=openai_api_key,
        )
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key)

        # pgvector 확장 활성화 + 테이블 생성
        with Session(self.engine) as session:
            session.exec(text("CREATE EXTENSION IF NOT EXISTS vector"))
            session.commit()
        SQLModel.metadata.create_all(self.engine)

    async def upload_document(
        self,
        content: str,
        source: str,
        rag_key: str,
    ) -> int:
        """문서를 청킹하고 임베딩하여 pgvector에 저장.

        Returns:
            저장된 청크 수
        """
        chunks = chunk_text(content, chunk_size=500, overlap=100)
        print(f"청크 수: {len(chunks)}")

        # 배치 임베딩: 청크를 한 번에 보내 API 호출 횟수 최소화
        vectors = await self.embeddings.aembed_documents(chunks)

        with Session(self.engine) as session:
            for chunk_text_content, vector in zip(chunks, vectors):
                chunk = DocumentChunk(
                    content=chunk_text_content,
                    source=source,
                    rag_key=rag_key,
                    embedding=vector,
                )
                session.add(chunk)
            session.commit()

        return len(chunks)

    async def search(
        self,
        query: str,
        rag_key: str,
        top_k: int = 5,
    ) -> List[str]:
        """질문과 가장 유사한 청크를 cosine similarity로 검색.

        pgvector cosine distance 연산자: <=>
        - 값 범위: 0(동일) ~ 2(완전 반대)
        - ORDER BY embedding <=> query_vector: 가장 유사한 순서

        실제 코드에서는 임계값(threshold) 필터링도 추가됨.
        """
        query_vector = await self.embeddings.aembed_query(query)

        with Session(self.engine) as session:
            # pgvector cosine similarity 검색
            results = session.exec(
                select(DocumentChunk)
                .where(DocumentChunk.rag_key == rag_key)
                .order_by(
                    DocumentChunk.embedding.op("<=>")(query_vector)
                )
                .limit(top_k)
            ).all()

        return [r.content for r in results]

    def build_context_prompt(self, retrieved_chunks: List[str]) -> str:
        """검색된 청크들을 system_prompt에 주입할 컨텍스트 문자열로 조합."""
        if not retrieved_chunks:
            return ""

        context = "\n\n---\n\n".join(retrieved_chunks)
        return f"""다음 참고 문서를 바탕으로 답변하세요:

{context}

위 문서에 없는 내용은 '제공된 문서에 해당 정보가 없습니다'라고 답변하세요.
"""

    async def ask(self, question: str, rag_key: str) -> str:
        """RAG 전체 파이프라인: 검색 → 컨텍스트 주입 → LLM 응답."""
        from langchain_core.messages import HumanMessage, SystemMessage

        # 1. 유사 청크 검색
        chunks = await self.search(question, rag_key)
        print(f"검색된 청크 수: {len(chunks)}")

        # 2. 시스템 프롬프트에 컨텍스트 주입
        context_prompt = self.build_context_prompt(chunks)
        system_prompt = context_prompt or "당신은 유용한 AI 어시스턴트입니다."

        # 3. LLM 호출
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]
        response = await self.llm.ainvoke(messages)
        return str(response.content)


# ── 실행 예시 ──────────────────────────────────────────────────────────────────

async def main():
    """RAG 파이프라인 예시."""
    import os

    pipeline = SimpleRAGPipeline(
        db_url=f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
               f"@{os.getenv('POSTGRES_HOST', 'localhost')}:5432/{os.getenv('POSTGRES_DB')}",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # 문서 업로드
    sample_doc = textwrap.dedent("""
        LangGraph는 LangChain 팀이 만든 상태 기계 기반 LLM 오케스트레이션 프레임워크입니다.
        주요 특징:
        - StateGraph: 노드(함수)와 엣지(흐름)로 복잡한 멀티스텝 AI 워크플로우를 정의
        - Checkpoint: PostgreSQL, SQLite 등에 상태를 저장하여 대화 연속성 보장
        - Streaming: 토큰 단위 실시간 스트리밍 지원
        - 조건부 라우팅: LLM의 판단에 따라 동적으로 다음 단계 결정

        LangGraph vs LangChain:
        - LangChain: 선형적인 체인(Chain) 구조
        - LangGraph: 순환, 분기, 병렬 실행이 가능한 그래프 구조
        - 복잡한 에이전트 워크플로우에는 LangGraph가 적합
    """)

    count = await pipeline.upload_document(
        content=sample_doc,
        source="langgraph_intro.txt",
        rag_key="langchain-docs",
    )
    print(f"{count}개 청크 저장 완료\n")

    # 검색 및 질의응답
    answer = await pipeline.ask(
        question="LangGraph와 LangChain의 차이점은?",
        rag_key="langchain-docs",
    )
    print(f"답변: {answer}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
