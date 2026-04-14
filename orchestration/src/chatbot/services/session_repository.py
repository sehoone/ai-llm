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
        """Create a new chat session.

        Args:
            session_id: Unique session identifier (UUID string).
            user_id: The owner's user ID.
            name: Optional display name for the session.

        Returns:
            ChatSession: The newly created session record.
        """
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
        """Retrieve a chat session by its ID.

        Args:
            session_id: The session identifier.

        Returns:
            Optional[ChatSession]: The session record, or None if not found.
        """
        def _sync():
            with Session(self.engine) as db:
                return db.get(ChatSession, session_id)
        return await asyncio.to_thread(_sync)

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """Retrieve all sessions for a user, ordered by most recent first.

        Args:
            user_id: The user's ID.

        Returns:
            List[ChatSession]: All sessions belonging to the user.
        """
        def _sync():
            with Session(self.engine) as db:
                statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc())
                return db.exec(statement).all()
        return await asyncio.to_thread(_sync)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session and its cascade-deleted messages.

        Args:
            session_id: The session identifier.

        Returns:
            bool: True if deleted, False if the session was not found.
        """
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
        """Update the display name of a chat session.

        Args:
            session_id: The session identifier.
            title: The new name to set.
        """
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
        """Persist a user question and assistant answer as a single message record.

        Args:
            session_id: The session this interaction belongs to.
            question: The user's question text.
            answer: The assistant's answer text.
            is_deep_thinking: Whether deep thinking mode was active (stored for reference).

        Returns:
            ChatMessage: The saved message record.
        """
        def _sync():
            with Session(self.engine) as db:
                message = ChatMessage(session_id=session_id, question=question, answer=answer)
                db.add(message)
                db.commit()
                db.refresh(message)
                return message
        return await asyncio.to_thread(_sync)

    async def get_chat_messages(self, session_id: str) -> List[ChatMessage]:
        """Retrieve all chat messages for a session, ordered by creation time.

        Args:
            session_id: The session identifier.

        Returns:
            List[ChatMessage]: Messages in chronological order.
        """
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
        """Retrieve paginated chat history across all users (admin use).

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            List[dict]: Chat message records joined with session and user info.
        """
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
        """Retrieve a single chat message by its ID with session and user info.

        Args:
            message_id: The message record ID.

        Returns:
            Optional[dict]: The message dict, or None if not found.
        """
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
