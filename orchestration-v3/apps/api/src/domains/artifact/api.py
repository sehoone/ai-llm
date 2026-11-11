"""artifact 도메인 라우터 (ADR-0013). web `api/artifacts.ts` 경로·필드 정렬.

- `router` → `/api/v1/artifacts` (인증).
- `public_router` → `/api/v1/public/artifacts` (미인증 공개 링크).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.artifact.schema import (
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
from src.domains.artifact.service import ArtifactService
from src.platform.auth.dependencies import get_current_user
from src.platform.user.model import User

router = APIRouter()
public_router = APIRouter()


def _parse_session_id(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


# ── 인증 ──
@router.get("", response_model=ApiResponse[ArtifactListResponse])
def list_artifacts(
    session_id: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ArtifactListResponse]:
    arts = ArtifactService(session).list_artifacts(user, _parse_session_id(session_id))
    return ApiResponse.ok(ArtifactListResponse(items=[ArtifactSummary.from_model(a) for a in arts]))


@router.get("/{artifact_id}", response_model=ApiResponse[ArtifactDetail])
def get_artifact(
    artifact_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[ArtifactDetail]:
    art, content = ArtifactService(session).get_detail(user, artifact_id)
    return ApiResponse.ok(ArtifactDetail.from_models(art, content))


@router.get("/{artifact_id}/versions", response_model=ApiResponse[ArtifactVersionListResponse])
def list_versions(
    artifact_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[ArtifactVersionListResponse]:
    versions = ArtifactService(session).list_versions(user, artifact_id)
    return ApiResponse.ok(
        ArtifactVersionListResponse(items=[ArtifactVersionResponse.from_model(v) for v in versions])
    )


@router.get("/{artifact_id}/versions/{version}", response_model=ApiResponse[ArtifactVersionResponse])
def get_version(
    artifact_id: str,
    version: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ArtifactVersionResponse]:
    ver = ArtifactService(session).get_version(user, artifact_id, version)
    return ApiResponse.ok(ArtifactVersionResponse.from_model(ver))


@router.delete("/{artifact_id}", response_model=ApiResponse[None])
def delete_artifact(
    artifact_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[None]:
    ArtifactService(session).delete(user, artifact_id)
    return ApiResponse.ok(None)


@router.post("/{artifact_id}/publish", response_model=ApiResponse[PublishResponse])
def publish_artifact(
    artifact_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[PublishResponse]:
    token = ArtifactService(session).publish(user, artifact_id)
    return ApiResponse.ok(PublishResponse(public_token=token))


@router.get("/{artifact_id}/data", response_model=ApiResponse[ArtifactDataResponse])
def get_artifact_data(
    artifact_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[ArtifactDataResponse]:
    data = ArtifactService(session).get_data(user, artifact_id)
    return ApiResponse.ok(ArtifactDataResponse(data=data))


@router.put("/{artifact_id}/data", response_model=ApiResponse[ArtifactDataResponse])
def set_artifact_data(
    artifact_id: str,
    body: ArtifactDataUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[ArtifactDataResponse]:
    ArtifactService(session).set_data(user, artifact_id, body.data)
    return ApiResponse.ok(ArtifactDataResponse(data=body.data))


# ── 공개(미인증) ──
@public_router.get("/{public_token}", response_model=ApiResponse[PublicArtifactResponse])
def get_public_artifact(
    public_token: str, session: Session = Depends(get_session)
) -> ApiResponse[PublicArtifactResponse]:
    result = ArtifactService(session).get_public(public_token)
    if result is None:
        raise HTTPException(status_code=404, detail="Published artifact not found")
    return ApiResponse.ok(PublicArtifactResponse(**result))


@public_router.get("/{public_token}/data", response_model=ApiResponse[ArtifactDataResponse])
def get_public_artifact_data(
    public_token: str, session: Session = Depends(get_session)
) -> ApiResponse[ArtifactDataResponse]:
    data = ArtifactService(session).get_public_data(public_token)
    if data is None:
        raise HTTPException(status_code=404, detail="Published artifact not found")
    return ApiResponse.ok(ArtifactDataResponse(data=data))


@public_router.put("/{public_token}/data", response_model=ApiResponse[ArtifactDataResponse])
def set_public_artifact_data(
    public_token: str, body: ArtifactDataUpdate, session: Session = Depends(get_session)
) -> ApiResponse[ArtifactDataResponse]:
    ok = ArtifactService(session).set_public_data(public_token, body.data)
    if not ok:
        raise HTTPException(status_code=404, detail="Published artifact not found")
    return ApiResponse.ok(ArtifactDataResponse(data=body.data))
