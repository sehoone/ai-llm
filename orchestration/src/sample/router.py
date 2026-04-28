"""샘플 라우터 — 모든 샘플 모듈을 /sample 접두사로 집계.

최종 URL 구조:
    GET  /api/v1/sample/                           — 샘플 인덱스
    POST /api/v1/sample/basic-chat/chat            — 기본 LangGraph 채팅
    POST /api/v1/sample/basic-chat/stream          — 기본 스트리밍
    GET  /api/v1/sample/basic-chat/history         — 대화 히스토리 조회

    POST /api/v1/sample/deep-thinking/chat         — 딥씽킹 채팅
    POST /api/v1/sample/deep-thinking/stream       — 딥씽킹 스트리밍

    GET  /api/v1/sample/llm/info                   — LLM 서비스 현황
    POST /api/v1/sample/llm/call                   — LLM 직접 호출
    GET  /api/v1/sample/llm/circuit-breakers       — Circuit Breaker 상태

    POST /api/v1/sample/rag/upload                 — 문서 업로드 (청킹+임베딩)
    POST /api/v1/sample/rag/search                 — 유사도 검색
    POST /api/v1/sample/rag/ask                    — RAG 기반 Q&A
    DELETE /api/v1/sample/rag/docs                 — 샘플 문서 삭제

    POST /api/v1/sample/patterns/stream/basic      — 기본 SSE 스트리밍 패턴
    POST /api/v1/sample/patterns/stream/sectioned  — 섹션 헤더 스트리밍 패턴
    GET  /api/v1/sample/patterns/rate-limit-test   — 레이트 리밋 테스트 (5/min)
    GET  /api/v1/sample/patterns/middleware-info   — 미들웨어 체인 정보

    GET  /api/v1/sample/workflow/node-types        — 노드 타입 목록
    GET  /api/v1/sample/workflow/presets           — 예시 워크플로우 정의
    POST /api/v1/sample/workflow/run               — 워크플로우 실행
    POST /api/v1/sample/workflow/run/stream        — 워크플로우 실행 (SSE)
"""

from fastapi import APIRouter

from src.sample._01_basic_chat_agent.api import router as basic_chat_router
from src.sample._02_deep_thinking.api import router as deep_thinking_router
from src.sample._03_llm_service.api import router as llm_router
from src.sample._04_rag_pipeline.api import router as rag_router
from src.sample._05_fastapi_patterns.api import router as patterns_router
from src.sample._06_workflow_engine.api import router as workflow_router

sample_router = APIRouter()

sample_router.include_router(basic_chat_router,   prefix="/basic-chat",    tags=["sample-basic-chat"])
sample_router.include_router(deep_thinking_router, prefix="/deep-thinking", tags=["sample-deep-thinking"])
sample_router.include_router(llm_router,           prefix="/llm",           tags=["sample-llm-service"])
sample_router.include_router(rag_router,           prefix="/rag",           tags=["sample-rag"])
sample_router.include_router(patterns_router,      prefix="/patterns",      tags=["sample-patterns"])
sample_router.include_router(workflow_router,      prefix="/workflow",      tags=["sample-workflow"])


@sample_router.get(
    "/",
    tags=["sample"],
    summary="샘플 API 인덱스",
    description="학습용 샘플 엔드포인트 목록을 반환합니다. Swagger UI: /docs",
)
async def sample_index():
    return {
        "description": "LLM 오케스트레이션 서비스 학습용 샘플 API",
        "swagger_ui": "/docs#/",
        "modules": {
            "basic-chat": {
                "prefix": "/api/v1/sample/basic-chat",
                "description": "LangGraph 기본 채팅 (체크포인트, 스트리밍)",
                "endpoints": [
                    "POST /chat",
                    "POST /stream",
                    "GET  /history",
                ],
            },
            "deep-thinking": {
                "prefix": "/api/v1/sample/deep-thinking",
                "description": "think → chat → verify 품질 루프",
                "endpoints": [
                    "POST /chat",
                    "POST /stream",
                ],
            },
            "llm": {
                "prefix": "/api/v1/sample/llm",
                "description": "멀티 프로바이더 LLM 서비스 (Circuit Breaker, 가중치 선택)",
                "endpoints": [
                    "GET  /info",
                    "POST /call",
                    "GET  /circuit-breakers",
                ],
            },
            "rag": {
                "prefix": "/api/v1/sample/rag",
                "description": "RAG 파이프라인 (문서 업로드 → 임베딩 → 검색 → Q&A)",
                "endpoints": [
                    "POST /upload",
                    "POST /search",
                    "POST /ask",
                    "DELETE /docs",
                ],
            },
            "patterns": {
                "prefix": "/api/v1/sample/patterns",
                "description": "FastAPI 패턴 (SSE 스트리밍, 레이트 리밋, 미들웨어)",
                "endpoints": [
                    "POST /stream/basic",
                    "POST /stream/sectioned",
                    "GET  /rate-limit-test",
                    "GET  /middleware-info",
                ],
            },
            "workflow": {
                "prefix": "/api/v1/sample/workflow",
                "description": "DAG 워크플로우 엔진 (병렬 실행, SSE 이벤트)",
                "endpoints": [
                    "GET  /node-types",
                    "GET  /presets",
                    "POST /run",
                    "POST /run/stream",
                ],
            },
        },
    }
