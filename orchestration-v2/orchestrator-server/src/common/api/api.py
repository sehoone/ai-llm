"""API v1 router configuration."""

from fastapi import APIRouter

from src.agent.api.agent_api import router as agent_router
from src.ai_overview.api.document_api import router as ai_overview_doc_router
from src.ai_overview.api.search_api import router as ai_overview_search_router
from src.chatbot.api.chatbot_api import router as chatbot_router
from src.chatbot.api.session_api import router as session_router
from src.chatbot.api.custom_gpts import router as custom_gpts_router
from src.rag.api.rag_api import router as rag_router
from src.rag.api.rag_group_api import router as rag_group_router
from src.voice_evaluation.api.voice_evaluation_api import router as voice_evaluation_router
from src.workflow.api.workflow_api import router as workflow_router
from src.workflow.api.execution_api import router as execution_router
from src.workflow.api.webhook_api import router as webhook_mgmt_router, webhook_router
from src.workflow.api.schedule_api import router as schedule_router
from src.workflow.api.endpoint_api import router as endpoint_mgmt_router, run_router
from src.sample.router import sample_router
from src.common.logging import logger

api_router = APIRouter()

# ── LLM/RAG/Workflow — orchestrator 담당 ─────────────────────────────────────
api_router.include_router(agent_router, prefix="/agents", tags=["agents"])
api_router.include_router(ai_overview_doc_router, prefix="/ai-overview/documents", tags=["ai-overview"])
api_router.include_router(ai_overview_search_router, prefix="/ai-overview", tags=["ai-overview"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(custom_gpts_router, prefix="/gpts", tags=["custom-gpts"])
api_router.include_router(session_router, prefix="/chatbot", tags=["chatbot-session"])
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
api_router.include_router(rag_group_router, prefix="/rag", tags=["rag-groups"])
api_router.include_router(voice_evaluation_router, prefix="/voice-evaluation", tags=["voice-evaluation"])
api_router.include_router(workflow_router, prefix="/workflows", tags=["workflows"])
api_router.include_router(execution_router, prefix="/workflows", tags=["workflow-executions"])
api_router.include_router(webhook_mgmt_router, prefix="/workflows", tags=["workflow-webhooks"])
api_router.include_router(schedule_router, prefix="/workflows", tags=["workflow-schedules"])
api_router.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(endpoint_mgmt_router, prefix="/workflows", tags=["workflow-endpoints"])
api_router.include_router(sample_router, prefix="/sample", tags=["sample"])
# catch-all — must be registered last to avoid shadowing other routes
api_router.include_router(run_router, prefix="/run", tags=["dynamic-api"])

# ── 아래 라우터는 platform-server 이관으로 제거됨 ────────────────────────────
# auth_router     → platform-server /api/v1/auth/*
# api_key_router  → platform-server /api/v1/api-keys/*
# user_router     → platform-server /api/v1/users/*
# llm_resource_router → platform-server /api/v1/llm-resources/*


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}
