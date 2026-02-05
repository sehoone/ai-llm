"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication and chatbot functionality.
"""

from fastapi import APIRouter

from src.auth.api.auth_api import router as auth_router
from src.chatbot.api.chatbot_api import router as chatbot_router
from src.chatbot.api.session_api import router as session_router
from src.rag.api.rag_api import router as rag_router
from src.voice_evaluation.api.voice_evaluation_api import router as voice_evaluation_router
from src.user.api.user_api import router as user_router
from src.common.logging import logger

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(user_router, prefix="/users", tags=["users"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(session_router, prefix="/chatbot", tags=["chatbot-session"])
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
api_router.include_router(voice_evaluation_router, prefix="/voice-evaluation", tags=["voice-evaluation"])


@api_router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}
