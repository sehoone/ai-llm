"""Shared database session context manager."""

from contextlib import contextmanager

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from src.common.logging import logger


@contextmanager
def managed_session(engine):
    """Session context manager with automatic rollback and error logging on SQLAlchemyError."""
    with Session(engine) as db:
        try:
            yield db
        except SQLAlchemyError:
            db.rollback()
            logger.error("db_operation_failed", exc_info=True)
            raise
