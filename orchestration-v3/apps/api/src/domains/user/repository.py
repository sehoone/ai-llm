from sqlmodel import Session, select

from src.domains.user.model import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_subject(self, idp_subject: str) -> User | None:
        return self.session.exec(
            select(User).where(User.idp_subject == idp_subject)
        ).first()

    def list(self, limit: int = 20, offset: int = 0) -> list[User]:
        return list(
            self.session.exec(select(User).order_by(User.id).offset(offset).limit(limit)).all()
        )

    def exists_username(self, username: str) -> bool:
        return self.session.exec(select(User.id).where(User.username == username)).first() is not None

    def exists_email(self, email: str) -> bool:
        return self.session.exec(select(User.id).where(User.email == email)).first() is not None

    def save(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
