"""Session repository mixin — CRUD for ChatSession and ChatMessage models."""

import asyncio
from typing import List, Optional

from sqlmodel import Session, select

from src.common.logging import logger
from src.chatbot.models.session_model import Session as ChatSession
from src.chatbot.models.message_model import ChatMessage
from src.user.models.user_model import User


class SessionRepositoryMixin:
    """Mixin providing ChatSession and ChatMessage database operations.

    Requires ``self.engine`` to be set by the host class.
    All sync DB calls are offloaded to a thread pool via asyncio.to_thread.
    """

    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        def _sync():
            with Session(self.engine) as db:
                chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
                db.add(chat_session)
                db.commit()
                db.refresh(chat_session)
                logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
                return chat_session
        return await asyncio.to_thread(_sync)

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        def _sync():
            with Session(self.engine) as db:
                return db.get(ChatSession, session_id)
        return await asyncio.to_thread(_sync)

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        def _sync():
            with Session(self.engine) as db:
                statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc())
                return db.exec(statement).all()
        return await asyncio.to_thread(_sync)

    async def delete_session(self, session_id: str) -> bool:
        def _sync():
            with Session(self.engine) as db:
                chat_session = db.get(ChatSession, session_id)
                if not chat_session:
                    return False
                db.delete(chat_session)
                db.commit()
                logger.info("session_deleted", session_id=session_id)
                return True
        return await asyncio.to_thread(_sync)

    async def update_session_name(self, session_id: str, title: str) -> None:
        def _sync():
            with Session(self.engine) as db:
                chat_session = db.exec(select(ChatSession).where(ChatSession.id == session_id)).one_or_none()
                if chat_session:
                    chat_session.name = title
                    db.add(chat_session)
                    db.commit()
                    db.refresh(chat_session)
                    logger.info("session_name_updated", session_id=session_id, new_title=title)
                else:
                    logger.warning("session_not_found_for_update", session_id=session_id)
        try:
            await asyncio.to_thread(_sync)
        except Exception as e:
            logger.error("update_session_name_failed", session_id=session_id, error=str(e))
            raise

    async def save_chat_interaction(self, session_id: str, question: str, answer: str, is_deep_thinking: bool = False) -> ChatMessage:
        def _sync():
            with Session(self.engine) as db:
                message = ChatMessage(session_id=session_id, question=question, answer=answer)
                db.add(message)
                db.commit()
                db.refresh(message)
                return message
        return await asyncio.to_thread(_sync)

    async def get_chat_messages(self, session_id: str) -> List[ChatMessage]:
        def _sync():
            with Session(self.engine) as db:
                statement = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
                return db.exec(statement).all()
        return await asyncio.to_thread(_sync)

    async def delete_chat_messages(self, session_id: str) -> None:
        """Delete all chat messages for a session."""
        def _sync():
            with Session(self.engine) as db:
                messages = db.exec(select(ChatMessage).where(ChatMessage.session_id == session_id)).all()
                for msg in messages:
                    db.delete(msg)
                db.commit()
                logger.info("chat_messages_deleted", session_id=session_id)
        await asyncio.to_thread(_sync)

    async def get_all_chat_history(self, limit: int = 100, offset: int = 0) -> List[dict]:
        def _sync():
            with Session(self.engine) as db:
                statement = (
                    select(ChatMessage, ChatSession, User)
                    .join(ChatSession, ChatMessage.session_id == ChatSession.id)
                    .join(User, ChatSession.user_id == User.id)
                    .order_by(ChatMessage.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                results = db.exec(statement).all()
                return [
                    {
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "user_email": user.email,
                        "question": msg.question,
                        "answer": msg.answer,
                        "created_at": msg.created_at,
                        "session_name": chat_session.name,
                    }
                    for msg, chat_session, user in results
                ]
        return await asyncio.to_thread(_sync)

    async def get_chat_message_by_id(self, message_id: int) -> Optional[dict]:
        def _sync():
            with Session(self.engine) as db:
                statement = (
                    select(ChatMessage, ChatSession, User)
                    .join(ChatSession, ChatMessage.session_id == ChatSession.id)
                    .join(User, ChatSession.user_id == User.id)
                    .where(ChatMessage.id == message_id)
                )
                result = db.exec(statement).first()
                if not result:
                    return None
                msg, chat_session, user = result
                return {
                    "id": msg.id,
                    "session_id": msg.session_id,
                    "user_email": user.email,
                    "question": msg.question,
                    "answer": msg.answer,
                    "created_at": msg.created_at,
                    "session_name": chat_session.name,
                }
        return await asyncio.to_thread(_sync)
