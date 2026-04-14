"""Custom GPT management service."""

from typing import List, Optional
from uuid import uuid4
from sqlmodel import select, Session

from src.chatbot.models.custom_gpt_model import CustomGPT
from src.chatbot.schemas.custom_gpt_schema import CustomGPTCreate, CustomGPTUpdate
from src.common.services.database import database_service

class CustomGPTService:
    """Service for CRUD operations on user-defined Custom GPT bots."""

    async def create_gpt(self, gpt_create: CustomGPTCreate, user_id: int) -> CustomGPT:
        """Create a new Custom GPT for a user.

        Args:
            gpt_create: Creation parameters (name, instructions, model, etc.).
            user_id: The ID of the owning user.

        Returns:
            CustomGPT: The newly created Custom GPT record.
        """
        rag_key = gpt_create.rag_key or f"gpt_{uuid4().hex}"
        gpt = CustomGPT(
            user_id=user_id,
            name=gpt_create.name,
            description=gpt_create.description,
            instructions=gpt_create.instructions,
            rag_key=rag_key,
            is_public=gpt_create.is_public,
            model=gpt_create.model
        )
        
        with Session(database_service.engine) as session:
            session.add(gpt)
            session.commit()
            session.refresh(gpt)
            return gpt

    async def get_gpt(self, gpt_id: str) -> Optional[CustomGPT]:
        """Retrieve a Custom GPT by its ID.

        Args:
            gpt_id: The unique ID of the Custom GPT.

        Returns:
            Optional[CustomGPT]: The Custom GPT record, or None if not found.
        """
        with Session(database_service.engine) as session:
            statement = select(CustomGPT).where(CustomGPT.id == gpt_id)
            result = session.exec(statement)
            return result.first()

    async def list_gpts(self, user_id: int) -> List[CustomGPT]:
        """List all Custom GPTs owned by a user.

        Args:
            user_id: The ID of the user.

        Returns:
            List[CustomGPT]: All Custom GPT records belonging to the user.
        """
        with Session(database_service.engine) as session:
            statement = select(CustomGPT).where(CustomGPT.user_id == user_id)
            result = session.exec(statement)
            return result.all()

    async def update_gpt(self, gpt_id: str, update_data: CustomGPTUpdate, user_id: int) -> Optional[CustomGPT]:
        """Update a Custom GPT's fields.

        Args:
            gpt_id: The ID of the Custom GPT to update.
            update_data: Fields to update (only set fields are applied).
            user_id: The owner's user ID (used to scope the update).

        Returns:
            Optional[CustomGPT]: The updated record, or None if not found / not owned.
        """
        with Session(database_service.engine) as session:
            statement = select(CustomGPT).where(CustomGPT.id == gpt_id, CustomGPT.user_id == user_id)
            result = session.exec(statement)
            gpt = result.first()
            if not gpt:
                return None

            hero_data = update_data.model_dump(exclude_unset=True)
            for key, value in hero_data.items():
                setattr(gpt, key, value)

            session.add(gpt)
            session.commit()
            session.refresh(gpt)
            return gpt

    async def delete_gpt(self, gpt_id: str, user_id: int) -> bool:
        """Delete a Custom GPT owned by a user.

        Args:
            gpt_id: The ID of the Custom GPT to delete.
            user_id: The owner's user ID (used to scope the deletion).

        Returns:
            bool: True if deleted, False if not found or not owned by the user.
        """
        with Session(database_service.engine) as session:
            statement = select(CustomGPT).where(CustomGPT.id == gpt_id, CustomGPT.user_id == user_id)
            result = session.exec(statement)
            gpt = result.first()
            if not gpt:
                return False

            session.delete(gpt)
            session.commit()
            return True

custom_gpt_service = CustomGPTService()
