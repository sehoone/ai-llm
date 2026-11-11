from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session

from src.platform.llm_resource.model import LlmResource
from src.platform.llm_resource.repository import LlmResourceRepository
from src.platform.llm_resource.schema import (
    ChatModelResponse,
    LlmResourceCreateRequest,
    LlmResourceResponse,
    LlmResourceUpdateRequest,
)


class LlmResourceService:
    def __init__(self, session: Session) -> None:
        self.repo = LlmResourceRepository(session)

    def chat_models(self) -> list[ChatModelResponse]:
        return [ChatModelResponse.from_model(r) for r in self.repo.list_active_chat_models()]

    def list(self, resource_type: str | None = None) -> list[LlmResourceResponse]:
        rows = self.repo.list_by_type(resource_type) if resource_type else self.repo.list_all()
        return [LlmResourceResponse.from_model(r) for r in rows]

    def get(self, resource_id: int) -> LlmResourceResponse:
        return LlmResourceResponse.from_model(self._find(resource_id))

    def create(self, req: LlmResourceCreateRequest) -> LlmResourceResponse:
        resource = LlmResource(**req.model_dump())
        return LlmResourceResponse.from_model(self.repo.save(resource))

    def update(self, resource_id: int, req: LlmResourceUpdateRequest) -> LlmResourceResponse:
        resource = self._find(resource_id)
        patch = req.model_dump(exclude_unset=True)
        # 빈 api_key는 기존 값 유지
        if not patch.get("api_key"):
            patch.pop("api_key", None)
        for field, value in patch.items():
            setattr(resource, field, value)
        resource.updated_at = datetime.utcnow()
        return LlmResourceResponse.from_model(self.repo.save(resource))

    def toggle_active(self, resource_id: int) -> LlmResourceResponse:
        resource = self._find(resource_id)
        resource.is_active = not resource.is_active
        resource.updated_at = datetime.utcnow()
        return LlmResourceResponse.from_model(self.repo.save(resource))

    def delete(self, resource_id: int) -> None:
        self.repo.delete(self._find(resource_id))

    def _find(self, resource_id: int) -> LlmResource:
        resource = self.repo.get(resource_id)
        if resource is None:
            raise HTTPException(status_code=404, detail="LLM resource not found")
        return resource
