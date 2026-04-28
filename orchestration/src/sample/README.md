# Sample Code — LLM Orchestration Service

이 디렉토리는 프로젝트의 핵심 패턴을 학습할 수 있는 샘플 코드 모음입니다.
실제 운영 코드(`src/common/`, `src/agent/` 등)를 단순화하여 개념을 명확하게 전달합니다.

## 학습 순서

| 디렉토리 | 주제 | 핵심 개념 |
|---|---|---|
| `01_basic_chat_agent/` | LangGraph 기본 에이전트 | StateGraph, Checkpoint, 스트리밍 |
| `02_deep_thinking/` | 딥씽킹 에이전트 | think → chat → verify 루프 |
| `03_llm_service/` | 멀티 프로바이더 LLM | Circuit Breaker, 우선순위 가중치 선택 |
| `04_rag_pipeline/` | RAG 파이프라인 | 문서 임베딩, 벡터 검색, 컨텍스트 주입 |
| `05_fastapi_patterns/` | FastAPI 패턴 | SSE 스트리밍, JWT 인증, 레이트 리밋 |

## 실제 코드와의 대응

```
샘플 코드                          실제 운영 코드
─────────────────────────────────────────────────────────
01_basic_chat_agent/agent.py  →  src/common/langgraph/graph.py
02_deep_thinking/nodes.py     →  src/common/langgraph/_nodes.py
03_llm_service/llm_service.py →  src/common/services/llm.py
04_rag_pipeline/pipeline.py   →  src/rag/services/rag_service.py
05_fastapi_patterns/          →  src/common/middleware.py + src/chatbot/api/
```

## 전제 조건

샘플을 실행하려면 프로젝트 루트에 아래 환경 변수가 설정된 `.env.development` 파일이 필요합니다:

```env
OPENAI_API_KEY=sk-...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=llmonl
JWT_SECRET_KEY=...
```

## 아키텍처 요약

```
Client Request
     │
     ▼
FastAPI Router (src/chatbot/api/ or src/agent/api/)
     │
     ▼
LangGraphAgent.get_response() / get_stream_response()
     │
     ├─ LangGraph StateGraph ──────────────────────────────────────────────┐
     │    ├── [think]  전략 수립 (딥씽킹 모드 또는 복잡한 질문)             │
     │    ├── [chat]   메인 LLM 응답                                        │
     │    ├── [tool_call] 툴 실행 후 chat으로 복귀                           │
     │    └── [verify] 품질 평가 → 승인(END) or 피드백 → chat 재시도         │
     │                                                                      │
     ├─ LLMService ──────────────────────────────────────────────────────── │
     │    ├── DB에서 LLMResource 목록 조회 (60초 캐싱)                       │
     │    ├── Circuit Breaker로 장애 리소스 제외                              │
     │    ├── Priority DESC + Weighted Random 순서로 정렬                    │
     │    └── 모두 실패 시 LLMRegistry(정적 목록) circular fallback           │
     │                                                                      │
     └─ RAG Context ─────────────────────────────────────────────────────── │
          ├── rag_key로 벡터 검색 수행                                        │
          └── 검색 결과를 시스템 프롬프트에 주입                               │
                                                                            │
PostgreSQL: 체크포인트 저장 (thread_id = session_id) ◄────────────────────┘
```
