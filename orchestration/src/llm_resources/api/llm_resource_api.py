from typing import List
from fastapi import APIRouter, HTTPException
from src.common.services.database import database_service
from src.llm_resources.schemas.llm_resource_schemas import LLMResourceCreate, LLMResourceResponse, LLMResourceUpdate

router = APIRouter()

@router.get("/", response_model=List[LLMResourceResponse])
async def read_llm_resources():
    return await database_service.get_llm_resources()

@router.post("/", response_model=LLMResourceResponse)
async def create_llm_resource(resource: LLMResourceCreate):
    return await database_service.create_llm_resource(resource)

@router.get("/{id}", response_model=LLMResourceResponse)
async def read_llm_resource(id: int):
    resource = await database_service.get_llm_resource(id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

@router.put("/{id}", response_model=LLMResourceResponse)
async def update_llm_resource(id: int, resource: LLMResourceUpdate):
    updated = await database_service.update_llm_resource(id, resource)
    if not updated:
        raise HTTPException(status_code=404, detail="Resource not found")
    return updated

@router.delete("/{id}")
async def delete_llm_resource(id: int):
    deleted = await database_service.delete_llm_resource(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found")
    return {"status": "success"}
