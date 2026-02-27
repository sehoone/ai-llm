"""User repository mixin — CRUD operations for the User model."""

from typing import List, Optional

from sqlmodel import Session, select

from src.common.logging import logger
from src.user.models.user_model import User


class UserRepositoryMixin:
    """Mixin providing User-related database operations.

    Requires ``self.engine`` to be set by the host class.
    """

    async def create_user(self, email: str, password: str, username: str, role: str = "user", status: str = "active") -> User:
        with Session(self.engine) as session:
            user = User(email=email, hashed_password=password, username=username, role=role, status=status)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("user_created", email=email)
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        with Session(self.engine) as session:
            return session.get(User, user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        with Session(self.engine) as session:
            return session.exec(select(User).where(User.email == email)).first()

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        with Session(self.engine) as session:
            return session.exec(select(User).offset(skip).limit(limit)).all()

    async def update_user(self, user_id: int, user_update: dict) -> Optional[User]:
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                return None
            for key, value in user_update.items():
                if value is not None:
                    setattr(user, key, value)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    async def delete_user(self, user_id: int) -> bool:
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            if not user:
                return False
            session.delete(user)
            session.commit()
            return True

    async def delete_user_by_email(self, email: str) -> bool:
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                return False
            session.delete(user)
            session.commit()
            logger.info("user_deleted", email=email)
            return True
