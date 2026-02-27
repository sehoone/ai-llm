"""Shared dependency helpers for chatbot API endpoints."""

from fastapi import HTTPException

from src.chatbot.models.session_model import Session as ChatSession
from src.chatbot.models.gpt_session_model import GPTSession
from src.common.services.database import database_service
from src.user.models.user_model import User


async def get_owned_chat_session(session_id: str, user: User) -> ChatSession:
    """Fetch a ChatSession and verify the user owns it.

    Raises:
        HTTPException 404: If the session does not exist.
        HTTPException 403: If the session belongs to another user.
    """
    session = await database_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot access other sessions")
    return session


async def get_owned_gpt_session(session_id: str, gpt_id: str, user: User) -> GPTSession:
    """Fetch a GPTSession and verify it belongs to the given GPT and user.

    Raises:
        HTTPException 404: If the session does not exist or belongs to a different GPT.
        HTTPException 403: If the session belongs to another user.
    """
    session = await database_service.get_gpt_session(session_id)
    if not session or session.custom_gpt_id != gpt_id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot access other sessions")
    return session
