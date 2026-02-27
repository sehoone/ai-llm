"""LLM resource repository mixin — CRUD for LLMResource model."""

from typing import List, Optional

from sqlmodel import Session, select

from src.llm_resources.models.llm_resource_model import LLMResource
from src.llm_resources.schemas.llm_resource_schemas import LLMResourceCreate, LLMResourceUpdate


class LLMResourceRepositoryMixin:
    """Mixin providing LLMResource database operations.

    Requires ``self.engine`` to be set by the host class.
    """

    async def get_llm_resources(self) -> List[LLMResource]:
        with Session(self.engine) as session:
            return session.exec(select(LLMResource).order_by(LLMResource.priority.desc())).all()

    async def get_llm_resource(self, id: int) -> Optional[LLMResource]:
        with Session(self.engine) as session:
            return session.get(LLMResource, id)

    async def create_llm_resource(self, resource: LLMResourceCreate) -> LLMResource:
        with Session(self.engine) as session:
            db_resource = LLMResource.model_validate(resource)
            session.add(db_resource)
            session.commit()
            session.refresh(db_resource)
            return db_resource

    async def update_llm_resource(self, id: int, resource: LLMResourceUpdate) -> Optional[LLMResource]:
        with Session(self.engine) as session:
            db_resource = session.get(LLMResource, id)
            if not db_resource:
                return None
            db_resource.sqlmodel_update(resource.model_dump(exclude_unset=True))
            session.add(db_resource)
            session.commit()
            session.refresh(db_resource)
            return db_resource

    async def delete_llm_resource(self, id: int) -> bool:
        with Session(self.engine) as session:
            resource = session.get(LLMResource, id)
            if not resource:
                return False
            session.delete(resource)
            session.commit()
            return True
