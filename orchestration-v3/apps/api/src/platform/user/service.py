from datetime import datetime

from sqlmodel import Session

from src.core.exceptions import ConflictError, NotFoundError
from src.core.security import hash_password
from src.platform.user.model import User
from src.platform.user.repository import UserRepository
from src.platform.user.schema import (
    AdminUserUpdateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = UserRepository(session)

    def create(self, req: UserCreateRequest) -> User:
        if self.repo.exists_username(req.username):
            raise ConflictError("Username already exists")
        if self.repo.exists_email(req.email):
            raise ConflictError("Email already exists")
        user = User(
            username=req.username,
            email=req.email,
            hashed_password=hash_password(req.password),
            role=req.role,
        )
        return self.repo.save(user)

    def get(self, user_id: int) -> User:
        user = self.repo.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def list(self, limit: int = 20, offset: int = 0) -> list[User]:
        return self.repo.list(limit=limit, offset=offset)

    def update_me(self, user_id: int, req: UserUpdateRequest) -> User:
        user = self.get(user_id)
        self._apply_profile(user, req.username, req.email)
        return self.repo.save(user)

    def admin_update(self, user_id: int, req: AdminUserUpdateRequest) -> User:
        user = self.get(user_id)
        self._apply_profile(user, req.username, req.email)
        if req.status is not None:
            user.status = req.status
        return self.repo.save(user)

    def deactivate(self, user_id: int) -> None:
        user = self.get(user_id)
        user.status = "inactive"
        user.updated_at = datetime.utcnow()
        self.repo.save(user)

    def _apply_profile(self, user: User, username: str | None, email: str | None) -> None:
        if email is not None and email != user.email:
            if self.repo.exists_email(email):
                raise ConflictError("Email already exists")
            user.email = email
        if username is not None and username != user.username:
            if self.repo.exists_username(username):
                raise ConflictError("Username already exists")
            user.username = username
        user.updated_at = datetime.utcnow()
