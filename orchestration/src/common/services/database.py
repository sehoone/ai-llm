"""Database service — engine setup and unified repository interface."""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlmodel import Session, create_engine, select

from src.common.config import Environment, settings
from src.common.logging import logger
from src.user.services.user_repository import UserRepositoryMixin
from src.chatbot.services.session_repository import SessionRepositoryMixin
from src.chatbot.services.gpt_repository import GPTRepositoryMixin
from src.llm_resources.services.llm_resource_repository import LLMResourceRepositoryMixin


class DatabaseService(
    UserRepositoryMixin,
    SessionRepositoryMixin,
    GPTRepositoryMixin,
    LLMResourceRepositoryMixin,
):
    """Unified database service.

    Composes domain-specific repository mixins so call sites can use a single
    ``database_service`` instance for all database operations.  Engine creation
    and connection-pool configuration live here; all query logic lives in the
    individual repository mixins.
    """

    def __init__(self):
        try:
            pool_size = settings.POSTGRES_POOL_SIZE
            max_overflow = settings.POSTGRES_MAX_OVERFLOW

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
                pool_timeout=30,
                pool_recycle=1800,
            )

            logger.info(
                "database_initialized",
                environment=settings.ENVIRONMENT.value,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        except SQLAlchemyError as e:
            logger.error("database_initialization_error", error=str(e), environment=settings.ENVIRONMENT.value)
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise

    def get_db_session(self):
        """Yield a database session for use as a FastAPI dependency."""
        with Session(self.engine) as session:
            yield session

    def get_session_maker(self) -> Session:
        """Return a new database session (for non-dependency use)."""
        return Session(self.engine)

    async def health_check(self) -> bool:
        """Return True if the database connection is healthy."""
        try:
            with Session(self.engine) as session:
                session.exec(select(1)).first()
                return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False


# Singleton — import this everywhere instead of instantiating DatabaseService directly.
database_service = DatabaseService()
