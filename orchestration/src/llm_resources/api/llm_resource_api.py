from typing import List
from fastapi import APIRouter, Depends, HTTPException
from src.auth.api.auth_api import get_current_user
from src.common.services.database import database_service
from src.llm_resources.schemas.llm_resource_schemas import LLMResourceCreate, LLMResourceResponse, LLMResourceUpdate
from src.user.models.user_model import User, UserRole

router = APIRouter()


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/", response_model=List[LLMResourceResponse])
async def read_llm_resources(user: User = Depends(_require_admin)):
    return await database_service.get_llm_resources()


@router.post("/", response_model=LLMResourceResponse)
async def create_llm_resource(resource: LLMResourceCreate, user: User = Depends(_require_admin)):
    return await database_service.create_llm_resource(resource)


@router.get("/{id}", response_model=LLMResourceResponse)
async def read_llm_resource(id: int, user: User = Depends(_require_admin)):
    resource = await database_service.get_llm_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


@router.put("/{id}", response_model=LLMResourceResponse)
async def update_llm_resource(id: int, resource: LLMResourceUpdate, user: User = Depends(_require_admin)):
    updated = await database_service.update_llm_resource(id, resource)
    if not updated:
        raise HTTPException(status_code=404, detail="Resource not found")
    return updated


@router.delete("/{id}")
async def delete_llm_resource(id: int, user: User = Depends(_require_admin)):
    deleted = await database_service.delete_llm_resource(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found")
    return {"status": "success"}
