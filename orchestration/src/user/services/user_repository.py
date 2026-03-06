"""User repository mixin — CRUD operations for the User model."""

import asyncio
from typing import List, Optional

from sqlmodel import Session, select

from src.common.logging import logger
from src.user.models.user_model import User


class UserRepositoryMixin:
    """Mixin providing User-related database operations.

    Requires ``self.engine`` to be set by the host class.
    All sync DB calls are offloaded to a thread pool via asyncio.to_thread.
    """

    async def create_user(self, email: str, password: str, username: str, role: str = "user", status: str = "active") -> User:
        def _sync():
            with Session(self.engine) as db:
                user = User(email=email, hashed_password=password, username=username, role=role, status=status)
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info("user_created", email=email)
                return user
        return await asyncio.to_thread(_sync)

    async def get_user(self, user_id: int) -> Optional[User]:
        def _sync():
            with Session(self.engine) as db:
                return db.get(User, user_id)
        return await asyncio.to_thread(_sync)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        def _sync():
            with Session(self.engine) as db:
                return db.exec(select(User).where(User.email == email)).first()
        return await asyncio.to_thread(_sync)

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        def _sync():
            with Session(self.engine) as db:
                return db.exec(select(User).offset(skip).limit(limit)).all()
        return await asyncio.to_thread(_sync)

    async def update_user(self, user_id: int, user_update: dict) -> Optional[User]:
        def _sync():
            with Session(self.engine) as db:
                user = db.get(User, user_id)
                if not user:
                    return None
                for key, value in user_update.items():
                    if value is not None:
                        setattr(user, key, value)
                db.add(user)
                db.commit()
                db.refresh(user)
                return user
        return await asyncio.to_thread(_sync)

    async def delete_user(self, user_id: int) -> bool:
        def _sync():
            with Session(self.engine) as db:
                user = db.get(User, user_id)
                if not user:
                    return False
                db.delete(user)
                db.commit()
                return True
        return await asyncio.to_thread(_sync)

    async def delete_user_by_email(self, email: str) -> bool:
        def _sync():
            with Session(self.engine) as db:
                user = db.exec(select(User).where(User.email == email)).first()
                if not user:
                    return False
                db.delete(user)
                db.commit()
                logger.info("user_deleted", email=email)
                return True
        return await asyncio.to_thread(_sync)
