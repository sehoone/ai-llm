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
        """Create a new user record.

        Args:
            email: The user's email address.
            password: Pre-hashed password string.
            username: Display name for the user.
            role: Role string (``"user"``, ``"admin"``, ``"superadmin"``).
            status: Account status (``"active"`` or ``"inactive"``).

        Returns:
            User: The newly created user record.
        """
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
        """Retrieve a user by primary key.

        Args:
            user_id: The user's integer ID.

        Returns:
            Optional[User]: The user record, or None if not found.
        """
        def _sync():
            with Session(self.engine) as db:
                return db.get(User, user_id)
        return await asyncio.to_thread(_sync)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by email address.

        Args:
            email: The user's email address.

        Returns:
            Optional[User]: The matching user, or None if not found.
        """
        def _sync():
            with Session(self.engine) as db:
                return db.exec(select(User).where(User.email == email)).first()
        return await asyncio.to_thread(_sync)

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieve a paginated list of all users.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List[User]: Paginated user records.
        """
        def _sync():
            with Session(self.engine) as db:
                return db.exec(select(User).offset(skip).limit(limit)).all()
        return await asyncio.to_thread(_sync)

    async def update_user(self, user_id: int, user_update: dict) -> Optional[User]:
        """Update a user's fields.

        Only non-None values in ``user_update`` are applied.

        Args:
            user_id: The ID of the user to update.
            user_update: Dictionary of field names to new values.

        Returns:
            Optional[User]: The updated user record, or None if not found.
        """
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
        """Delete a user by ID.

        Args:
            user_id: The ID of the user to delete.

        Returns:
            bool: True if deleted, False if not found.
        """
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
        """Delete a user by email address.

        Args:
            email: The email of the user to delete.

        Returns:
            bool: True if deleted, False if not found.
        """
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
