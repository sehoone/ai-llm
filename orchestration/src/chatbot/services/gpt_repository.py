"""GPT repository mixin — CRUD for GPTSession and GPTChatMessage models."""

import asyncio
from typing import List, Optional

from sqlmodel import Session, select

from src.common.logging import logger
from src.chatbot.models.gpt_session_model import GPTSession
from src.chatbot.models.gpt_message_model import GPTChatMessage


class GPTRepositoryMixin:
    """Mixin providing GPTSession and GPTChatMessage database operations.

    Requires ``self.engine`` to be set by the host class.
    All sync DB calls are offloaded to a thread pool via asyncio.to_thread.
    """

    async def create_gpt_session(self, session_id: str, user_id: int, custom_gpt_id: str, name: str = "") -> GPTSession:
        def _sync():
            with Session(self.engine) as db:
                gpt_session = GPTSession(id=session_id, user_id=user_id, custom_gpt_id=custom_gpt_id, name=name)
                db.add(gpt_session)
                db.commit()
                db.refresh(gpt_session)
                logger.info("gpt_session_created", session_id=session_id, user_id=user_id, custom_gpt_id=custom_gpt_id)
                return gpt_session
        return await asyncio.to_thread(_sync)

    async def get_gpt_session(self, session_id: str) -> Optional[GPTSession]:
        def _sync():
            with Session(self.engine) as db:
                return db.get(GPTSession, session_id)
        return await asyncio.to_thread(_sync)

    async def get_user_gpt_sessions(self, user_id: int, custom_gpt_id: str) -> List[GPTSession]:
        def _sync():
            with Session(self.engine) as db:
                statement = (
                    select(GPTSession)
                    .where(GPTSession.user_id == user_id, GPTSession.custom_gpt_id == custom_gpt_id)
                    .order_by(GPTSession.created_at.desc())
                )
                return db.exec(statement).all()
        return await asyncio.to_thread(_sync)

    async def update_gpt_session_name(self, session_id: str, name: str) -> Optional[GPTSession]:
        def _sync():
            with Session(self.engine) as db:
                gpt_session = db.get(GPTSession, session_id)
                if not gpt_session:
                    return None
                gpt_session.name = name
                db.add(gpt_session)
                db.commit()
                db.refresh(gpt_session)
                logger.info("gpt_session_name_updated", session_id=session_id, name=name)
                return gpt_session
        return await asyncio.to_thread(_sync)

    async def delete_gpt_session(self, session_id: str) -> bool:
        def _sync():
            with Session(self.engine) as db:
                gpt_session = db.get(GPTSession, session_id)
                if not gpt_session:
                    return False
                db.delete(gpt_session)
                db.commit()
                logger.info("gpt_session_deleted", session_id=session_id)
                return True
        return await asyncio.to_thread(_sync)

    async def save_gpt_chat_interaction(self, session_id: str, question: str, answer: str) -> GPTChatMessage:
        def _sync():
            with Session(self.engine) as db:
                message = GPTChatMessage(session_id=session_id, question=question, answer=answer)
                db.add(message)
                db.commit()
                db.refresh(message)
                return message
        return await asyncio.to_thread(_sync)

    async def get_gpt_chat_messages(self, session_id: str) -> List[GPTChatMessage]:
        def _sync():
            with Session(self.engine) as db:
                statement = (
                    select(GPTChatMessage)
                    .where(GPTChatMessage.session_id == session_id)
                    .order_by(GPTChatMessage.created_at)
                )
                return db.exec(statement).all()
        return await asyncio.to_thread(_sync)

    async def delete_gpt_chat_messages(self, session_id: str) -> None:
        def _sync():
            with Session(self.engine) as db:
                messages = db.exec(select(GPTChatMessage).where(GPTChatMessage.session_id == session_id)).all()
                for msg in messages:
                    db.delete(msg)
                db.commit()
                logger.info("gpt_chat_messages_deleted", session_id=session_id)
        await asyncio.to_thread(_sync)
