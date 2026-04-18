"""RAG group and key management endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.auth.api.auth_api import get_current_user
from src.common.logging import logger
from src.rag.schemas.rag_group_schema import (
    RagGroupCreate,
    RagGroupResponse,
    RagGroupUpdate,
    RagKeyCreate,
    RagKeyResponse,
    RagKeyUpdate,
)
from src.rag.services.rag_group_service import rag_group_service
from src.user.models.user_model import User

router = APIRouter()


# ── Groups ────────────────────────────────────────────────────────────────────

@router.get("/groups", response_model=List[RagGroupResponse], summary="RAG 그룹 목록")
async def list_groups(user: User = Depends(get_current_user)):
    return await rag_group_service.list_groups(user.id)


@router.post("/groups", response_model=RagGroupResponse, summary="RAG 그룹 생성")
async def create_group(data: RagGroupCreate, user: User = Depends(get_current_user)):
    return await rag_group_service.create_group(data, user.id)


@router.put("/groups/{group_id}", response_model=RagGroupResponse, summary="RAG 그룹 수정")
async def update_group(group_id: str, data: RagGroupUpdate, user: User = Depends(get_current_user)):
    result = await rag_group_service.update_group(group_id, data, user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Group not found")
    return result


@router.delete("/groups/{group_id}", summary="RAG 그룹 삭제")
async def delete_group(group_id: str, user: User = Depends(get_current_user)):
    success = await rag_group_service.delete_group(group_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"message": "Group deleted"}


@router.get("/groups/{group_id}/keys", response_model=List[RagKeyResponse], summary="그룹 내 키 목록")
async def list_group_keys(group_id: str, user: User = Depends(get_current_user)):
    group = await rag_group_service.get_group(group_id, user.id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return await rag_group_service.list_keys(user.id, rag_group=group.name)


# ── Keys ──────────────────────────────────────────────────────────────────────

@router.get("/keys", response_model=List[RagKeyResponse], summary="RAG 키 목록")
async def list_keys(
    rag_group: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
):
    return await rag_group_service.list_keys(user.id, rag_group=rag_group)


@router.post("/keys", response_model=RagKeyResponse, summary="RAG 키 생성")
async def create_key(data: RagKeyCreate, user: User = Depends(get_current_user)):
    return await rag_group_service.create_key(data, user.id)


@router.put("/keys/{key_id}", response_model=RagKeyResponse, summary="RAG 키 수정")
async def update_key(key_id: str, data: RagKeyUpdate, user: User = Depends(get_current_user)):
    result = await rag_group_service.update_key(key_id, data, user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Key not found")
    return result


@router.delete("/keys/{key_id}", summary="RAG 키 삭제")
async def delete_key(
    key_id: str,
    delete_docs: bool = Query(default=False, description="문서와 임베딩도 함께 삭제"),
    user: User = Depends(get_current_user),
):
    success = await rag_group_service.delete_key(key_id, user.id, delete_docs=delete_docs)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"message": "Key deleted"}
