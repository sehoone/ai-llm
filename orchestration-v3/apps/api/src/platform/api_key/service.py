import base64
import secrets
from datetime import datetime

from sqlmodel import Session

from src.core.exceptions import NotFoundError, PermissionDeniedError
from src.platform.api_key.model import ApiKey
from src.platform.api_key.repository import ApiKeyRepository
from src.platform.api_key.schema import ApiKeyCreateRequest, ApiKeyResponse


class ApiKeyService:
    def __init__(self, session: Session) -> None:
        self.repo = ApiKeyRepository(session)

    def list(self, user_id: int) -> list[ApiKeyResponse]:
        return [ApiKeyResponse.masked(k) for k in self.repo.list_by_user(user_id)]

    def create(self, user_id: int, req: ApiKeyCreateRequest) -> ApiKeyResponse:
        api_key = ApiKey(
            user_id=user_id,
            key=self._generate_key(),
            name=req.name,
            expires_at=req.expires_at,
        )
        return ApiKeyResponse.full(self.repo.save(api_key))

    def revoke(self, user_id: int, key_id: int) -> None:
        api_key = self.repo.get(key_id)
        if api_key is None:
            raise NotFoundError("API key not found")
        if api_key.user_id != user_id:
            raise PermissionDeniedError("Forbidden")
        api_key.is_active = False
        api_key.updated_at = datetime.utcnow()
        self.repo.save(api_key)

    @staticmethod
    def _generate_key() -> str:
        token = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        return f"sk-{token}"
