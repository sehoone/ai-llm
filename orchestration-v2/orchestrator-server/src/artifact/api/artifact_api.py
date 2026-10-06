"""Artifact API — list, read, version history, publish, and public access."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.artifact.models.artifact_model import Artifact
from src.artifact.schemas.artifact_schema import (
    ArtifactDataResponse,
    ArtifactDataUpdate,
    ArtifactDetail,
    ArtifactListResponse,
    ArtifactSummary,
    ArtifactVersionListResponse,
    ArtifactVersionResponse,
    PublicArtifactResponse,
    PublishResponse,
)

# Guard against unbounded interactive payloads.
MAX_ARTIFACT_DATA_BYTES = 256 * 1024
from src.auth.api.auth_api import get_current_user
from src.common.logging import logger
from src.common.services.database import database_service
from src.user.models.user_model import User, UserRole

router = APIRouter()


def _summary(art: Artifact) -> ArtifactSummary:
    return ArtifactSummary(
        id=art.id,
        session_id=art.session_id,
        identifier=art.identifier,
        artifact_type=art.artifact_type,
        title=art.title,
        current_version=art.current_version,
        is_published=art.is_published,
        public_token=art.public_token,
        created_at=art.created_at,
        updated_at=art.updated_at,
    )


async def _get_owned_artifact(artifact_id: str, user: User) -> Artifact:
    """Fetch an artifact, enforcing ownership (admins may access any)."""
    art = await database_service.get_artifact(artifact_id)
    if art is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    is_admin = user.role in (UserRole.ADMIN, UserRole.SUPERADMIN)
    if not is_admin and art.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return art


@router.get("", response_model=ArtifactListResponse, summary="아티펙트 목록 조회")
async def list_artifacts(
    session_id: Optional[str] = Query(default=None, description="세션 ID로 필터 (미지정 시 전체 라이브러리)"),
    user: User = Depends(get_current_user),
):
    """List the user's artifacts, optionally filtered to a single session."""
    if session_id:
        arts = await database_service.list_session_artifacts(session_id)
        # Ownership filter (admins see all rows regardless of owner).
        is_admin = user.role in (UserRole.ADMIN, UserRole.SUPERADMIN)
        arts = [a for a in arts if is_admin or a.user_id == user.id]
    else:
        arts = await database_service.list_user_artifacts(user.id)
    return ArtifactListResponse(items=[_summary(a) for a in arts])


@router.get("/{artifact_id}", response_model=ArtifactDetail, summary="아티펙트 상세 (현재 버전)")
async def get_artifact(artifact_id: str, user: User = Depends(get_current_user)):
    """Return artifact metadata plus the content of its current version."""
    art = await _get_owned_artifact(artifact_id, user)
    ver = await database_service.get_artifact_version(art.id, art.current_version)
    if ver is None:
        raise HTTPException(status_code=404, detail="Artifact version not found")
    summary = _summary(art)
    return ArtifactDetail(**summary.model_dump(), content=ver.content)


@router.get(
    "/{artifact_id}/versions",
    response_model=ArtifactVersionListResponse,
    summary="아티펙트 버전 히스토리",
)
async def get_artifact_versions(artifact_id: str, user: User = Depends(get_current_user)):
    """Return all versions of an artifact, newest first."""
    art = await _get_owned_artifact(artifact_id, user)
    versions = await database_service.get_artifact_versions(art.id)
    return ArtifactVersionListResponse(
        items=[
            ArtifactVersionResponse(version=v.version, content=v.content, created_at=v.created_at)
            for v in versions
        ]
    )


@router.get(
    "/{artifact_id}/versions/{version}",
    response_model=ArtifactVersionResponse,
    summary="아티펙트 특정 버전",
)
async def get_artifact_version(
    artifact_id: str, version: int, user: User = Depends(get_current_user)
):
    """Return a specific version of an artifact."""
    art = await _get_owned_artifact(artifact_id, user)
    ver = await database_service.get_artifact_version(art.id, version)
    if ver is None:
        raise HTTPException(status_code=404, detail="Artifact version not found")
    return ArtifactVersionResponse(version=ver.version, content=ver.content, created_at=ver.created_at)


@router.delete("/{artifact_id}", summary="아티펙트 삭제")
async def delete_artifact(artifact_id: str, user: User = Depends(get_current_user)):
    """Delete an artifact and all its versions (owner or admin only)."""
    art = await _get_owned_artifact(artifact_id, user)
    deleted = await database_service.delete_artifact(art.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"message": "Artifact deleted successfully"}


@router.post("/{artifact_id}/publish", response_model=PublishResponse, summary="아티펙트 공개 링크 발급")
async def publish_artifact(artifact_id: str, user: User = Depends(get_current_user)):
    """Publish an artifact and return its public token (idempotent)."""
    art = await _get_owned_artifact(artifact_id, user)
    token = await database_service.publish_artifact(art.id)
    if token is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return PublishResponse(public_token=token, is_published=True)


def _check_data_size(data: dict) -> None:
    """Reject interactive payloads larger than the allowed limit."""
    if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > MAX_ARTIFACT_DATA_BYTES:
        raise HTTPException(status_code=413, detail="Artifact data exceeds the size limit")


@router.get("/{artifact_id}/data", response_model=ArtifactDataResponse, summary="아티펙트 데이터 조회 (소유자)")
async def get_artifact_data(artifact_id: str, user: User = Depends(get_current_user)):
    """Read an artifact's interactive data (owner/admin)."""
    art = await _get_owned_artifact(artifact_id, user)
    data = await database_service.get_artifact_data(art.id)
    return ArtifactDataResponse(data=data)


@router.put("/{artifact_id}/data", response_model=ArtifactDataResponse, summary="아티펙트 데이터 저장 (소유자)")
async def set_artifact_data(
    artifact_id: str, body: ArtifactDataUpdate, user: User = Depends(get_current_user)
):
    """Replace an artifact's interactive data (owner/admin)."""
    art = await _get_owned_artifact(artifact_id, user)
    _check_data_size(body.data)
    await database_service.set_artifact_data(art.id, body.data)
    return ArtifactDataResponse(data=body.data)


# ── Public (unauthenticated) ────────────────────────────────────────────────

public_router = APIRouter()


@public_router.get(
    "/artifacts/{public_token}",
    response_model=PublicArtifactResponse,
    summary="공개 아티펙트 조회 (인증 불필요)",
)
async def get_public_artifact(public_token: str):
    """Fetch a published artifact's current version by its public token."""
    data = await database_service.get_public_artifact(public_token)
    if data is None:
        logger.info("public_artifact_not_found", token=public_token)
        raise HTTPException(status_code=404, detail="Published artifact not found")
    return PublicArtifactResponse(**data)


@public_router.get(
    "/artifacts/{public_token}/data",
    response_model=ArtifactDataResponse,
    summary="공개 아티펙트 데이터 조회 (인증 불필요)",
)
async def get_public_artifact_data(public_token: str):
    """Read interactive data for a published artifact via its public token."""
    art = await database_service.get_artifact_by_public_token(public_token)
    if art is None:
        raise HTTPException(status_code=404, detail="Published artifact not found")
    data = await database_service.get_artifact_data(art.id)
    return ArtifactDataResponse(data=data)


@public_router.put(
    "/artifacts/{public_token}/data",
    response_model=ArtifactDataResponse,
    summary="공개 아티펙트 데이터 저장 (협업 — 링크 소지자 누구나)",
)
async def set_public_artifact_data(public_token: str, body: ArtifactDataUpdate):
    """Write interactive data for a published artifact via its public token.

    Collaborative by design: anyone holding the public link may write. Use only
    for data that is safe to share-and-edit openly.
    """
    art = await database_service.get_artifact_by_public_token(public_token)
    if art is None:
        raise HTTPException(status_code=404, detail="Published artifact not found")
    _check_data_size(body.data)
    await database_service.set_artifact_data(art.id, body.data)
    return ArtifactDataResponse(data=body.data)
