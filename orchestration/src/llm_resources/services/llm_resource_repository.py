"""LLM resource repository mixin — CRUD for LLMResource model."""

import asyncio
from typing import List, Optional

from sqlmodel import Session, select

from src.llm_resources.models.llm_resource_model import LLMResource
from src.llm_resources.schemas.llm_resource_schemas import LLMResourceCreate, LLMResourceUpdate


class LLMResourceRepositoryMixin:
    """Mixin providing LLMResource database operations.

    Requires ``self.engine`` to be set by the host class.
    All sync DB calls are offloaded to a thread pool via asyncio.to_thread.
    """

    async def get_llm_resources(self) -> List[LLMResource]:
        def _sync():
            with Session(self.engine) as db:
                return db.exec(select(LLMResource).order_by(LLMResource.priority.desc())).all()
        return await asyncio.to_thread(_sync)

    async def get_llm_resource(self, id: int) -> Optional[LLMResource]:
        def _sync():
            with Session(self.engine) as db:
                return db.get(LLMResource, id)
        return await asyncio.to_thread(_sync)

    async def create_llm_resource(self, resource: LLMResourceCreate) -> LLMResource:
        def _sync():
            with Session(self.engine) as db:
                db_resource = LLMResource.model_validate(resource)
                db.add(db_resource)
                db.commit()
                db.refresh(db_resource)
                return db_resource
        return await asyncio.to_thread(_sync)

    async def update_llm_resource(self, id: int, resource: LLMResourceUpdate) -> Optional[LLMResource]:
        def _sync():
            with Session(self.engine) as db:
                db_resource = db.get(LLMResource, id)
                if not db_resource:
                    return None
                db_resource.sqlmodel_update(resource.model_dump(exclude_unset=True))
                db.add(db_resource)
                db.commit()
                db.refresh(db_resource)
                return db_resource
        return await asyncio.to_thread(_sync)

    async def delete_llm_resource(self, id: int) -> bool:
        def _sync():
            with Session(self.engine) as db:
                resource = db.get(LLMResource, id)
                if not resource:
                    return False
                db.delete(resource)
                db.commit()
                return True
        return await asyncio.to_thread(_sync)
