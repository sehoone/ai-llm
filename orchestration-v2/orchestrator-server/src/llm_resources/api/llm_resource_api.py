"""LLM 리소스 관리 — platform-server /api/v1/llm-resources/* 로 이관됨.

내부 LLM 라우팅(LLMService, EmbeddingService)은 database_service.get_llm_resources()를
직접 호출하므로 이 라우터 없이도 정상 동작한다.
"""

from fastapi import APIRouter

router = APIRouter()
