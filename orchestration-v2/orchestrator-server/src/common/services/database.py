"""Database service — engine setup and unified repository interface."""

import asyncio
from urllib.parse import quote_plus

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlmodel import Session, create_engine, select, text

from src.common.services.db_session import managed_session

from src.common.config import Environment, settings
from src.common.logging import logger
from src.user.services.user_repository import UserRepositoryMixin
from src.chatbot.services.session_repository import SessionRepositoryMixin
from src.chatbot.services.attachment_repository import AttachmentRepositoryMixin
from src.chatbot.services.gpt_repository import GPTRepositoryMixin
from src.llm_resources.services.llm_resource_repository import LLMResourceRepositoryMixin
from src.workflow.services.workflow_repository import WorkflowRepositoryMixin


class DatabaseService(
    UserRepositoryMixin,
    SessionRepositoryMixin,
    AttachmentRepositoryMixin,
    GPTRepositoryMixin,
    LLMResourceRepositoryMixin,
    WorkflowRepositoryMixin,
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

            logger.info(
                "database_connecting",
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                db=settings.POSTGRES_DB,
                schema=settings.POSTGRES_SCHEMA,
                user=settings.POSTGRES_USER,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )

            connection_url = (
                f"postgresql://{quote_plus(settings.POSTGRES_USER)}:{quote_plus(settings.POSTGRES_PASSWORD)}"
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

            self._register_pool_events()

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

    def _register_pool_events(self):
        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            logger.info("db_pool_new_connection", status="opened")

        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            logger.debug("db_pool_checkout", status="acquired")

        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            logger.debug("db_pool_checkin", status="returned")

        @event.listens_for(self.engine, "invalidate")
        def on_invalidate(dbapi_conn, connection_record, exception):
            logger.warning("db_pool_connection_invalidated", error=str(exception) if exception else None)

    def get_db_session(self):
        """Yield a database session for use as a FastAPI dependency."""
        with managed_session(self.engine) as session:
            yield session

    def get_session_maker(self) -> Session:
        """Return a new database session (for non-dependency use)."""
        return Session(self.engine)

    async def health_check(self) -> bool:
        """Return True if the database connection is healthy."""
        def _check() -> bool:
            with Session(self.engine) as session:
                result = session.exec(select(1)).first()
                schema_exists = session.execute(
                    text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :s").bindparams(s=settings.POSTGRES_SCHEMA)
                ).first()
                logger.info(
                    "database_health_check_ok",
                    ping=result,
                    schema=settings.POSTGRES_SCHEMA,
                    schema_exists=schema_exists is not None,
                )
                return True

        try:
            return await asyncio.to_thread(_check)
        except Exception as e:
            logger.error(
                "database_health_check_failed",
                error=str(e),
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                db=settings.POSTGRES_DB,
                schema=settings.POSTGRES_SCHEMA,
            )
            return False


# Singleton — import this everywhere instead of instantiating DatabaseService directly.
database_service = DatabaseService()
