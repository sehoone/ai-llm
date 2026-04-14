"""LLM resource management endpoints. Admin access required for all operations."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from src.auth.api.auth_api import get_current_user
from src.common.services.database import database_service
from src.llm_resources.schemas.llm_resource_schemas import LLMResourceCreate, LLMResourceResponse, LLMResourceUpdate
from src.user.models.user_model import User, UserRole

router = APIRouter()


def _require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that restricts access to admin and superadmin users.

    Raises:
        HTTPException: 403 if the user does not have admin privileges.
    """
    if user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/", response_model=List[LLMResourceResponse])
async def read_llm_resources(user: User = Depends(_require_admin)):
    """List all LLM resources ordered by priority. Admin only.

    Returns:
        List[LLMResourceResponse]: All registered LLM resource configurations.
    """
    return await database_service.get_llm_resources()


@router.post("/", response_model=LLMResourceResponse)
async def create_llm_resource(resource: LLMResourceCreate, user: User = Depends(_require_admin)):
    """Create a new LLM resource configuration. Admin only.

    Args:
        resource: LLM resource creation parameters.

    Returns:
        LLMResourceResponse: The created resource.
    """
    return await database_service.create_llm_resource(resource)


@router.get("/{id}", response_model=LLMResourceResponse)
async def read_llm_resource(id: int, user: User = Depends(_require_admin)):
    """Get a specific LLM resource by ID. Admin only.

    Args:
        id: The resource ID.

    Returns:
        LLMResourceResponse: The resource configuration.

    Raises:
        HTTPException: 404 if not found.
    """
    resource = await database_service.get_llm_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


@router.put("/{id}", response_model=LLMResourceResponse)
async def update_llm_resource(id: int, resource: LLMResourceUpdate, user: User = Depends(_require_admin)):
    """Update an LLM resource configuration. Admin only.

    Args:
        id: The resource ID to update.
        resource: Fields to update.

    Returns:
        LLMResourceResponse: The updated resource.

    Raises:
        HTTPException: 404 if not found.
    """
    updated = await database_service.update_llm_resource(id, resource)
    if not updated:
        raise HTTPException(status_code=404, detail="Resource not found")
    return updated


@router.delete("/{id}")
async def delete_llm_resource(id: int, user: User = Depends(_require_admin)):
    """Delete an LLM resource configuration. Admin only.

    Args:
        id: The resource ID to delete.

    Returns:
        dict: Success status.

    Raises:
        HTTPException: 404 if not found.
    """
    deleted = await database_service.delete_llm_resource(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found")
    return {"status": "success"}
