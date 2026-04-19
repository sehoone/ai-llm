"""Attachment repository mixin — CRUD for ChatAttachment model."""

import asyncio
from typing import Dict, List, Optional

from sqlmodel import Session, select

from src.chatbot.models.attachment_model import ChatAttachment


class AttachmentRepositoryMixin:
    """Mixin providing ChatAttachment database operations.

    Requires ``self.engine`` to be set by the host class.
    """

    async def create_attachment(
        self,
        message_id: int,
        session_id: str,
        filename: str,
        content_type: str,
        file_size: int,
        storage_path: str,
    ) -> ChatAttachment:
        def _sync() -> ChatAttachment:
            with Session(self.engine) as db:
                attachment = ChatAttachment(
                    message_id=message_id,
                    session_id=session_id,
                    filename=filename,
                    content_type=content_type,
                    file_size=file_size,
                    storage_path=storage_path,
                )
                db.add(attachment)
                db.commit()
                db.refresh(attachment)
                return attachment

        return await asyncio.to_thread(_sync)

    async def get_attachment(self, attachment_id: int) -> Optional[ChatAttachment]:
        def _sync() -> Optional[ChatAttachment]:
            with Session(self.engine) as db:
                return db.get(ChatAttachment, attachment_id)

        return await asyncio.to_thread(_sync)

    async def get_attachments_by_message_ids(self, message_ids: List[int]) -> Dict[int, List[ChatAttachment]]:
        """Batch-fetch attachments for multiple messages.

        Returns a dict keyed by message_id to avoid N+1 queries.
        """
        def _sync() -> Dict[int, List[ChatAttachment]]:
            with Session(self.engine) as db:
                statement = (
                    select(ChatAttachment)
                    .where(ChatAttachment.message_id.in_(message_ids))
                    .order_by(ChatAttachment.created_at)
                )
                rows = db.exec(statement).all()
                result: Dict[int, List[ChatAttachment]] = {mid: [] for mid in message_ids}
                for row in rows:
                    result[row.message_id].append(row)
                return result

        return await asyncio.to_thread(_sync)

    async def delete_attachment(self, attachment_id: int) -> bool:
        def _sync() -> bool:
            with Session(self.engine) as db:
                attachment = db.get(ChatAttachment, attachment_id)
                if not attachment:
                    return False
                db.delete(attachment)
                db.commit()
                return True

        return await asyncio.to_thread(_sync)
