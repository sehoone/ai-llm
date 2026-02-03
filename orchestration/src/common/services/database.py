"""This file contains the database service for the application."""

from typing import (
    List,
    Optional,
)

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlalchemy import text
from sqlmodel import (
    Session,
    SQLModel,
    create_engine,
    select,
)

from src.common.config import (
    Environment,
    settings,
)
from src.common.logging import logger
from src.rag.models.document_model import Document
from src.chatbot.models.session_model import Session as ChatSession
from src.user.models.user_model import User
from src.rag.models.rag_embedding_model import RAGEmbedding
from src.chatbot.models.message_model import ChatMessage


class DatabaseService:
    """Service class for database operations.

    This class handles all database operations for Users, Sessions, and Messages.
    It uses SQLModel for ORM operations and maintains a connection pool.
    """

    def __init__(self):
        """Initialize database service with connection pool."""
        try:
            # Configure environment-specific database connection pool settings
            pool_size = settings.POSTGRES_POOL_SIZE
            max_overflow = settings.POSTGRES_MAX_OVERFLOW

            # Create engine with appropriate pool configuration
            connection_url = (
                f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
                f"?options=-csearch_path%3D{settings.POSTGRES_SCHEMA},public"
            )

            self.engine = create_engine(
                connection_url,
                pool_pre_ping=True,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=30,  # Connection timeout (seconds)
                pool_recycle=1800,  # Recycle connections after 30 minutes
            )

            # 테이블이 존재 하지 않으면 생성. SQLModel.metadata.create_all은 import된 모든 모델을 기준으로 테이블을 생성함.
            # SQLModel.metadata.create_all(self.engine)

            logger.info(
                "database_initialized",
                environment=settings.ENVIRONMENT.value,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        except SQLAlchemyError as e:
            logger.error("database_initialization_error", error=str(e), environment=settings.ENVIRONMENT.value)
            # In production, don't raise - allow app to start even with DB issues
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise



    async def create_user(self, email: str, password: str) -> User:
        """Create a new user.

        Args:
            email: User's email address
            password: Hashed password

        Returns:
            User: The created user
        """
        with Session(self.engine) as session:
            user = User(email=email, hashed_password=password)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("user_created", email=email)
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: The email of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            user = session.exec(statement).first()
            return user

    async def delete_user_by_email(self, email: str) -> bool:
        """Delete a user by email.

        Args:
            email: The email of the user to delete

        Returns:
            bool: True if deletion was successful, False if user not found
        """
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                return False

            session.delete(user)
            session.commit()
            logger.info("user_deleted", email=email)
            return True

    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        """Create a new chat session.

        Args:
            session_id: The ID for the new session
            user_id: The ID of the user who owns the session
            name: Optional name for the session (defaults to empty string)

        Returns:
            ChatSession: The created session
        """
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: The ID of the session to delete

        Returns:
            bool: True if deletion was successful, False if session not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                return False

            session.delete(chat_session)
            session.commit()
            logger.info("session_deleted", session_id=session_id)
            return True

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            Optional[ChatSession]: The session if found, None otherwise
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            return chat_session

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """Get all sessions for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List[ChatSession]: List of user's sessions
        """
        with Session(self.engine) as session:
            statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc())
            sessions = session.exec(statement).all()
            return sessions

    async def update_session_name(self, session_id: str, name: str) -> ChatSession:
        """Update a session's name.

        Args:
            session_id: The ID of the session to update
            name: The new name for the session

        Returns:
            ChatSession: The updated session

        Raises:
            HTTPException: If session is not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")

            chat_session.name = name
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_name_updated", session_id=session_id, name=name)
            return chat_session

    async def save_chat_interaction(self, session_id: str, question: str, answer: str, is_deep_thinking: bool = False) -> ChatMessage:
        """Save a chat interaction (question and answer) to the database.

        Args:
            session_id: The ID of the session
            question: The user's question
            answer: The assistant's answer
            is_deep_thinking: Whether the interaction used deep thinking

        Returns:
            ChatMessage: The saved interaction
        """
        with Session(self.engine) as session:
            # Note: Assuming ChatMessage model doesn't have is_deep_thinking column yet. 
            # If it does, add it here: is_deep_thinking=is_deep_thinking
            # If not, we just ignore the argument for now but keep the signature compatible with API call
            message = ChatMessage(session_id=session_id, question=question, answer=answer)
            session.add(message)
            session.commit()
            session.refresh(message)
            return message

    async def get_chat_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a session.

        Args:
            session_id: The ID of the session

        Returns:
            List[ChatMessage]: List of messages sorted by creation time
        """
        with Session(self.engine) as session:
            statement = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
            messages = session.exec(statement).all()
            return messages

    async def get_all_chat_history(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """Get all chat history with user details.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List[dict]: List of chat history records with user info
        """
        with Session(self.engine) as session:
            # Join ChatMessage, Session, and User
            statement = (
                select(ChatMessage, ChatSession, User)
                .join(ChatSession, ChatMessage.session_id == ChatSession.id)
                .join(User, ChatSession.user_id == User.id)
                .order_by(ChatMessage.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            
            results = session.exec(statement).all()
            
            history = []
            for message, chat_session, user in results:
                history.append({
                    "id": message.id,
                    "session_id": message.session_id,
                    "user_email": user.email,
                    "question": message.question,
                    "answer": message.answer,
                    "created_at": message.created_at,
                    "session_name": chat_session.name
                })
            
            return history

    async def update_session_name(self, session_id: str, title: str) -> None:
        """Update the name/title of a chat session.

        Args:
            session_id: The ID of the session to update
            title: The new title for the session
        """
        try:
            with Session(self.engine) as session:
                statement = select(ChatSession).where(ChatSession.id == session_id)
                chat_session = session.exec(statement).one_or_none()
                
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
            raise e

    async def get_chat_message_by_id(self, message_id: int) -> Optional[dict]:
        """Get a specific chat message by ID with user info.

        Args:
            message_id: The ID of the message

        Returns:
            Optional[dict]: The chat history record if found
        """
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
                
            message, chat_session, user = result
            return {
                "id": message.id,
                "session_id": message.session_id,
                "user_email": user.email,
                "question": message.question,
                "answer": message.answer,
                "created_at": message.created_at,
                "session_name": chat_session.name
            }

    def get_session_maker(self):
        """Get a session maker for creating database sessions.

        Returns:
            Session: A SQLModel session maker
        """
        return Session(self.engine)

    async def health_check(self) -> bool:
        """Check database connection health.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            with Session(self.engine) as session:
                # Execute a simple query to check connection
                session.exec(select(1)).first()
                return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False


# Create a singleton instance
database_service = DatabaseService()
