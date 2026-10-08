"""Custom GPT management service."""

import asyncio
from typing import List, Optional
from uuid import uuid4

from sqlmodel import select

from src.chatbot.models.custom_gpt_model import CustomGPT
from src.chatbot.models.gpt_session_model import GPTSession
from src.chatbot.models.gpt_message_model import GPTChatMessage
from src.chatbot.schemas.custom_gpt_schema import CustomGPTCreate, CustomGPTUpdate
from src.common.services.database import database_service
from src.common.services.db_session import managed_session


class CustomGPTService:
    """Service for CRUD operations on user-defined Custom GPT bots.

    All sync DB work runs under ``managed_session`` (automatic rollback on
    ``SQLAlchemyError``) and is offloaded to a thread pool via
    ``asyncio.to_thread`` so the event loop is never blocked — matching the
    repository-mixin pattern used elsewhere in the codebase.
    """

    async def create_gpt(self, gpt_create: CustomGPTCreate, user_id: int) -> CustomGPT:
        """Create a new Custom GPT for a user.

        Args:
            gpt_create: Creation parameters (name, instructions, model, etc.).
            user_id: The ID of the owning user.

        Returns:
            CustomGPT: The newly created Custom GPT record.
        """
        rag_key = gpt_create.rag_key or f"gpt_{uuid4().hex}"

        def _sync() -> CustomGPT:
            gpt = CustomGPT(
                user_id=user_id,
                name=gpt_create.name,
                description=gpt_create.description,
                instructions=gpt_create.instructions,
                rag_key=rag_key,
                is_public=gpt_create.is_public,
                model=gpt_create.model,
            )
            with managed_session(database_service.engine) as session:
                session.add(gpt)
                session.commit()
                session.refresh(gpt)
                return gpt

        return await asyncio.to_thread(_sync)

    async def get_gpt(self, gpt_id: str) -> Optional[CustomGPT]:
        """Retrieve a Custom GPT by its ID.

        Args:
            gpt_id: The unique ID of the Custom GPT.

        Returns:
            Optional[CustomGPT]: The Custom GPT record, or None if not found.
        """
        def _sync() -> Optional[CustomGPT]:
            with managed_session(database_service.engine) as session:
                return session.exec(select(CustomGPT).where(CustomGPT.id == gpt_id)).first()

        return await asyncio.to_thread(_sync)

    async def list_gpts(self, user_id: int) -> List[CustomGPT]:
        """List all Custom GPTs owned by a user.

        Args:
            user_id: The ID of the user.

        Returns:
            List[CustomGPT]: All Custom GPT records belonging to the user.
        """
        def _sync() -> List[CustomGPT]:
            with managed_session(database_service.engine) as session:
                return list(
                    session.exec(select(CustomGPT).where(CustomGPT.user_id == user_id)).all()
                )

        return await asyncio.to_thread(_sync)

    async def update_gpt(self, gpt_id: str, update_data: CustomGPTUpdate, user_id: int) -> Optional[CustomGPT]:
        """Update a Custom GPT's fields.

        Args:
            gpt_id: The ID of the Custom GPT to update.
            update_data: Fields to update (only set fields are applied).
            user_id: The owner's user ID (used to scope the update).

        Returns:
            Optional[CustomGPT]: The updated record, or None if not found / not owned.
        """
        def _sync() -> Optional[CustomGPT]:
            with managed_session(database_service.engine) as session:
                gpt = session.exec(
                    select(CustomGPT).where(CustomGPT.id == gpt_id, CustomGPT.user_id == user_id)
                ).first()
                if not gpt:
                    return None

                update_fields = update_data.model_dump(exclude_unset=True)
                for key, value in update_fields.items():
                    setattr(gpt, key, value)

                session.add(gpt)
                session.commit()
                session.refresh(gpt)
                return gpt

        return await asyncio.to_thread(_sync)

    async def delete_gpt(self, gpt_id: str, user_id: int) -> bool:
        """Delete a Custom GPT owned by a user.

        Args:
            gpt_id: The ID of the Custom GPT to delete.
            user_id: The owner's user ID (used to scope the deletion).

        Returns:
            bool: True if deleted, False if not found or not owned by the user.
        """
        def _sync() -> bool:
            with managed_session(database_service.engine) as session:
                gpt = session.exec(
                    select(CustomGPT).where(CustomGPT.id == gpt_id, CustomGPT.user_id == user_id)
                ).first()
                if not gpt:
                    return False

                # gpt_session / gpt_chat_message reference custom_gpt without
                # ON DELETE CASCADE, so child sessions and their messages must be
                # removed explicitly before the Custom GPT itself.
                gpt_sessions = session.exec(
                    select(GPTSession).where(GPTSession.custom_gpt_id == gpt_id)
                ).all()
                session_ids = [s.id for s in gpt_sessions]
                if session_ids:
                    messages = session.exec(
                        select(GPTChatMessage).where(GPTChatMessage.session_id.in_(session_ids))
                    ).all()
                    for msg in messages:
                        session.delete(msg)
                    for s in gpt_sessions:
                        session.delete(s)

                session.delete(gpt)
                session.commit()
                return True

        return await asyncio.to_thread(_sync)


custom_gpt_service = CustomGPTService()
