from typing import Literal

from pydantic import BaseModel, Field

from src.platform.llm_resource.model import LlmResource

ResourceType = Literal["chat", "embedding"]


class LlmResourceCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    resource_type: ResourceType
    model_name: str | None = None
    provider: str = Field(min_length=1)
    api_base: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    deployment_name: str | None = None
    api_version: str | None = None
    region: str | None = None
    priority: int = Field(default=0, ge=0)
    weight: int = Field(default=1, ge=1)
    is_active: bool = True


class LlmResourceUpdateRequest(BaseModel):
    name: str | None = None
    resource_type: ResourceType | None = None
    model_name: str | None = None
    provider: str | None = None
    api_base: str | None = None
    api_key: str | None = None  # 빈 문자열이면 기존 유지
    deployment_name: str | None = None
    api_version: str | None = None
    region: str | None = None
    priority: int | None = Field(default=None, ge=0)
    weight: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class LlmResourceResponse(BaseModel):
    """api_key는 응답에서 제외 (민감 정보)."""

    id: int
    name: str
    resource_type: str
    model_name: str | None
    provider: str
    api_base: str
    deployment_name: str | None
    api_version: str | None
    region: str | None
    priority: int
    weight: int
    is_active: bool

    @classmethod
    def from_model(cls, r: LlmResource) -> "LlmResourceResponse":
        return cls(
            id=r.id, name=r.name, resource_type=r.resource_type, model_name=r.model_name,
            provider=r.provider, api_base=r.api_base, deployment_name=r.deployment_name,
            api_version=r.api_version, region=r.region, priority=r.priority,
            weight=r.weight, is_active=r.is_active,
        )


class ChatModelResponse(BaseModel):
    id: int
    name: str
    model_name: str | None

    @classmethod
    def from_model(cls, r: LlmResource) -> "ChatModelResponse":
        return cls(id=r.id, name=r.name, model_name=r.model_name)
