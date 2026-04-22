"""API key management service."""

from datetime import UTC, datetime, timedelta
from typing import List, Optional
import uuid
from sqlmodel import Session, select
from src.auth.models.api_key_model import ApiKey
from src.auth.schemas.api_key_schema import ApiKeyCreate
from src.auth.services.auth_service import create_access_token

class ApiKeyService:
    """Service for creating, retrieving, and revoking API keys."""

    def create_api_key(self, session: Session, user_id: int, key_data: ApiKeyCreate) -> ApiKey:
        """Create a new JWT-based API key for a user.

        Args:
            session: Database session.
            user_id: The ID of the user the key belongs to.
            key_data: API key creation parameters (name, expiry).

        Returns:
            ApiKey: The newly created API key record.
        """
        # Generate a JWT as the API Key
        expires_delta = None
        if key_data.expires_at:
             # Calculate delta
             now = datetime.now(UTC)
             # Ensure key_data.expires_at is timezone aware to compare
             expires_at = key_data.expires_at
             if expires_at.tzinfo is None:
                 expires_at = expires_at.replace(tzinfo=UTC)
                 
             if expires_at > now:
                 expires_delta = expires_at - now
        
        # Create a token with a special claim
        token_data = create_access_token(
            thread_id=str(user_id), 
            expires_delta=expires_delta,
            claims={"type": "api_key"}
        )
        generated_key = token_data.access_token
        
        db_key = ApiKey(
            user_id=user_id,
            key=generated_key,
            name=key_data.name,
            expires_at=key_data.expires_at,
            is_active=True
        )
        session.add(db_key)
        session.commit()
        session.refresh(db_key)
        return db_key

    def get_api_keys(self, session: Session, user_id: int) -> List[ApiKey]:
        """Return all active API keys belonging to a user.

        Args:
            session: Database session.
            user_id: The user's ID.

        Returns:
            List[ApiKey]: Active API keys for the user.
        """
        statement = select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.is_active == True)
        results = session.exec(statement)
        return results.all()

    def revoke_api_key(self, session: Session, key_id: int, user_id: int) -> Optional[ApiKey]:
        """Deactivate an API key by setting is_active to False.

        Args:
            session: Database session.
            key_id: The ID of the API key to revoke.
            user_id: The owner's user ID (used to scope the lookup).

        Returns:
            Optional[ApiKey]: The updated key record, or None if not found.
        """
        statement = select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        key = session.exec(statement).first()
        if key:
            key.is_active = False
            session.add(key)
            session.commit()
            session.refresh(key)
        return key

    def get_api_key_by_token(self, session: Session, token: str) -> Optional[ApiKey]:
        """Look up an active, non-expired API key by its token string.

        Args:
            session: Database session.
            token: The raw API key token.

        Returns:
            Optional[ApiKey]: The matching key record, or None if invalid/expired.
        """
        statement = select(ApiKey).where(ApiKey.key == token, ApiKey.is_active == True)
        key = session.exec(statement).first()
        if key and key.expires_at:
            expires_at = key.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at < datetime.now(UTC):
                return None
        return key

api_key_service = ApiKeyService()
