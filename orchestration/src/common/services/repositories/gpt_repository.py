"""GPT repository mixin — CRUD for GPTSession and GPTChatMessage models."""

from typing import List, Optional

from sqlmodel import Session, select

from src.common.logging import logger
from src.chatbot.models.gpt_session_model import GPTSession
from src.chatbot.models.gpt_message_model import GPTChatMessage


class GPTRepositoryMixin:
    """Mixin providing GPTSession and GPTChatMessage database operations.

    Requires ``self.engine`` to be set by the host class.
    """

    async def create_gpt_session(self, session_id: str, user_id: int, custom_gpt_id: str, name: str = "") -> GPTSession:
        with Session(self.engine) as session:
            gpt_session = GPTSession(id=session_id, user_id=user_id, custom_gpt_id=custom_gpt_id, name=name)
            session.add(gpt_session)
            session.commit()
            session.refresh(gpt_session)
            logger.info("gpt_session_created", session_id=session_id, user_id=user_id, custom_gpt_id=custom_gpt_id)
            return gpt_session

    async def get_gpt_session(self, session_id: str) -> Optional[GPTSession]:
        with Session(self.engine) as session:
            return session.get(GPTSession, session_id)

    async def get_user_gpt_sessions(self, user_id: int, custom_gpt_id: str) -> List[GPTSession]:
        with Session(self.engine) as session:
            statement = (
                select(GPTSession)
                .where(GPTSession.user_id == user_id, GPTSession.custom_gpt_id == custom_gpt_id)
                .order_by(GPTSession.created_at.desc())
            )
            return session.exec(statement).all()

    async def update_gpt_session_name(self, session_id: str, name: str) -> Optional[GPTSession]:
        with Session(self.engine) as session:
            gpt_session = session.get(GPTSession, session_id)
            if not gpt_session:
                return None
            gpt_session.name = name
            session.add(gpt_session)
            session.commit()
            session.refresh(gpt_session)
            logger.info("gpt_session_name_updated", session_id=session_id, name=name)
            return gpt_session

    async def delete_gpt_session(self, session_id: str) -> bool:
        with Session(self.engine) as session:
            gpt_session = session.get(GPTSession, session_id)
            if not gpt_session:
                return False
            session.delete(gpt_session)
            session.commit()
            logger.info("gpt_session_deleted", session_id=session_id)
            return True

    async def save_gpt_chat_interaction(self, session_id: str, question: str, answer: str) -> GPTChatMessage:
        with Session(self.engine) as session:
            message = GPTChatMessage(session_id=session_id, question=question, answer=answer)
            session.add(message)
            session.commit()
            session.refresh(message)
            return message

    async def get_gpt_chat_messages(self, session_id: str) -> List[GPTChatMessage]:
        with Session(self.engine) as session:
            statement = (
                select(GPTChatMessage)
                .where(GPTChatMessage.session_id == session_id)
                .order_by(GPTChatMessage.created_at)
            )
            return session.exec(statement).all()

    async def delete_gpt_chat_messages(self, session_id: str) -> None:
        with Session(self.engine) as session:
            messages = session.exec(select(GPTChatMessage).where(GPTChatMessage.session_id == session_id)).all()
            for msg in messages:
                session.delete(msg)
            session.commit()
            logger.info("gpt_chat_messages_deleted", session_id=session_id)
