from sqlmodel import Session, select

from src.domains.api_key.model import ApiKey


class ApiKeyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key_id: int) -> ApiKey | None:
        return self.session.get(ApiKey, key_id)

    def get_by_key(self, key: str) -> ApiKey | None:
        return self.session.exec(select(ApiKey).where(ApiKey.key == key)).first()

    def list_by_user(self, user_id: int) -> list[ApiKey]:
        return list(
            self.session.exec(
                select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.id.desc())
            ).all()
        )

    def save(self, api_key: ApiKey) -> ApiKey:
        self.session.add(api_key)
        self.session.commit()
        self.session.refresh(api_key)
        return api_key
