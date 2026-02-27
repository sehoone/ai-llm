"""Session repository mixin — CRUD for ChatSession and ChatMessage models."""

from typing import List, Optional

from sqlmodel import Session, select

from src.common.logging import logger
from src.chatbot.models.session_model import Session as ChatSession
from src.chatbot.models.message_model import ChatMessage
from src.user.models.user_model import User


class SessionRepositoryMixin:
    """Mixin providing ChatSession and ChatMessage database operations.

    Requires ``self.engine`` to be set by the host class.
    """

    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        with Session(self.engine) as session:
            return session.get(ChatSession, session_id)

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        with Session(self.engine) as session:
            statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc())
            return session.exec(statement).all()

    async def delete_session(self, session_id: str) -> bool:
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                return False
            session.delete(chat_session)
            session.commit()
            logger.info("session_deleted", session_id=session_id)
            return True

    async def update_session_name(self, session_id: str, title: str) -> None:
        try:
            with Session(self.engine) as session:
                chat_session = session.exec(select(ChatSession).where(ChatSession.id == session_id)).one_or_none()
                if chat_session:
                    chat_session.name = title
                    session.add(chat_session)
                    session.commit()
                    session.refresh(chat_session)
                    logger.info("session_name_updated", session_id=session_id, new_title=title)
                else:
                    logger.warning("session_not_found_for_update", session_id=session_id)
        except Exception as e:
            logger.error("update_session_name_failed", session_id=session_id, error=str(e))
            raise

    async def save_chat_interaction(self, session_id: str, question: str, answer: str, is_deep_thinking: bool = False) -> ChatMessage:
        with Session(self.engine) as session:
            message = ChatMessage(session_id=session_id, question=question, answer=answer)
            session.add(message)
            session.commit()
            session.refresh(message)
            return message

    async def get_chat_messages(self, session_id: str) -> List[ChatMessage]:
        with Session(self.engine) as session:
            statement = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
            return session.exec(statement).all()

    async def get_all_chat_history(self, limit: int = 100, offset: int = 0) -> List[dict]:
        with Session(self.engine) as session:
            statement = (
                select(ChatMessage, ChatSession, User)
                .join(ChatSession, ChatMessage.session_id == ChatSession.id)
                .join(User, ChatSession.user_id == User.id)
                .order_by(ChatMessage.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            results = session.exec(statement).all()
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

    async def get_chat_message_by_id(self, message_id: int) -> Optional[dict]:
        with Session(self.engine) as session:
            statement = (
                select(ChatMessage, ChatSession, User)
                .join(ChatSession, ChatMessage.session_id == ChatSession.id)
                .join(User, ChatSession.user_id == User.id)
                .where(ChatMessage.id == message_id)
            )
            result = session.exec(statement).first()
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
