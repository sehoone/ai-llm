"""Meeting-minutes API — upload audio, poll status, view transcript/minutes, publish."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from src.auth.api.auth_api import get_current_user
from src.common.config import settings
from src.common.logging import logger
from src.meeting_minutes.models.meeting_model import Meeting, MeetingStatus
from src.meeting_minutes.schemas.meeting_schema import (
    CreateMeetingResponse,
    MeetingDetailResponse,
    MeetingListResponse,
    MeetingSummary,
    MinutesResponse,
    PublishResponse,
    SegmentResponse,
    SpeakerMappingRequest,
    TranscriptResponse,
    UpdateMinutesRequest,
)
from src.meeting_minutes.services.meeting_service import meeting_service
from src.meeting_minutes.services.storage_service import storage_service
from src.user.models.user_model import User, UserRole

router = APIRouter()


async def _get_owned_meeting(meeting_id: str, user: User) -> Meeting:
    """Fetch a meeting, enforcing ownership (admins may access any)."""
    meeting = await meeting_service.get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    is_admin = user.role in (UserRole.ADMIN, UserRole.SUPERADMIN)
    if not is_admin and meeting.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return meeting


async def _read_capped(file: UploadFile, max_bytes: int) -> Optional[bytes]:
    """Read an upload into memory, aborting early once it exceeds ``max_bytes``.

    Returns None if the limit is exceeded, so an oversized (or malicious) upload
    is never fully buffered.
    """
    buf = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            return None
    return bytes(buf)


def _summary(m: Meeting) -> MeetingSummary:
    return MeetingSummary(
        id=m.id,
        title=m.title,
        status=m.status,
        audio_filename=m.audio_filename,
        audio_duration_sec=m.audio_duration_sec,
        language=m.language,
        transcription_provider=m.transcription_provider,
        artifact_id=m.artifact_id,
        public_token=m.public_token,
        error_message=m.error_message,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


@router.post("", response_model=CreateMeetingResponse, summary="회의 오디오 업로드 → 회의록 생성 시작")
async def create_meeting(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(default=""),
    language: str = Form(default=""),
    user: User = Depends(get_current_user),
):
    """Upload a recording and kick off transcription + summarization in the background."""
    max_bytes = settings.MEETING_MAX_AUDIO_MB * 1024 * 1024
    # Reject by declared size first (Content-Length), before reading anything.
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"오디오 크기({file.size / (1024 * 1024):.1f}MB)가 한도({settings.MEETING_MAX_AUDIO_MB}MB)를 초과합니다.",
        )
    # Cap the actual read too (handles missing/forged Content-Length).
    data = await _read_capped(file, max_bytes)
    if data is None:
        raise HTTPException(status_code=413, detail=f"오디오 크기가 한도({settings.MEETING_MAX_AUDIO_MB}MB)를 초과합니다.")
    if not data:
        raise HTTPException(status_code=400, detail="빈 오디오 파일입니다.")
    size_mb = len(data) / (1024 * 1024)

    object_key = await asyncio.to_thread(storage_service.save_sync, data, file.filename or "recording.webm")
    meeting = await meeting_service.create_meeting(
        user_id=user.id,
        title=title.strip(),
        object_key=object_key,
        filename=file.filename or "recording.webm",
        language=(language or settings.MEETING_DEFAULT_LOCALE),
    )

    background_tasks.add_task(meeting_service.process_meeting, meeting.id)
    logger.info("meeting_created", meeting_id=meeting.id, user_id=user.id, size_mb=round(size_mb, 2))
    return CreateMeetingResponse(id=meeting.id, status=meeting.status)


@router.get("", response_model=MeetingListResponse, summary="내 회의 목록")
async def list_meetings(user: User = Depends(get_current_user)):
    meetings = await meeting_service.list_meetings(user.id)
    return MeetingListResponse(items=[_summary(m) for m in meetings])


@router.get("/{meeting_id}", response_model=MeetingDetailResponse, summary="회의 상세 (상태 + 회의록)")
async def get_meeting(meeting_id: str, user: User = Depends(get_current_user)):
    meeting = await _get_owned_meeting(meeting_id, user)
    minutes_resp: Optional[MinutesResponse] = None
    latest = await meeting_service.get_latest_minutes(meeting_id)
    if latest is not None:
        try:
            content = json.loads(latest.content_json)
        except (ValueError, TypeError):
            content = {}
        minutes_resp = MinutesResponse(
            summary=latest.summary,
            content=content,
            model_used=latest.model_used,
            version=latest.version,
        )
    return MeetingDetailResponse(**_summary(meeting).model_dump(), minutes=minutes_resp)


@router.get("/{meeting_id}/audio", summary="저장된 오디오 재생/다운로드")
async def get_meeting_audio(
    meeting_id: str,
    request: Request,
    download: bool = Query(default=False, description="true면 첨부(다운로드), 기본은 인라인(재생)"),
    user: User = Depends(get_current_user),
):
    """Serve the stored audio for playback (inline) or download (attachment).

    S3 backend: proxies the object and forwards the ``Range`` header so the audio
    player can seek (206 Partial Content). Local backend: ``FileResponse`` (native
    range support).
    """
    meeting = await _get_owned_meeting(meeting_id, user)
    key = meeting.audio_object_key
    if not storage_service.exists(key):
        raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없습니다.")

    filename = meeting.audio_filename or f"{meeting_id}.audio"
    disposition = f'{"attachment" if download else "inline"}; filename="{filename}"'

    if not storage_service.use_s3:
        return FileResponse(
            path=storage_service.path_for(key),
            media_type=storage_service.content_type_for(key),
            filename=filename,
            content_disposition_type="attachment" if download else "inline",
        )

    range_header = request.headers.get("range")
    obj = await asyncio.to_thread(storage_service.get_object, key, range_header)
    headers = {
        "Content-Disposition": disposition,
        "Accept-Ranges": "bytes",
    }
    if obj["content_length"] is not None:
        headers["Content-Length"] = str(obj["content_length"])
    if obj["content_range"]:
        headers["Content-Range"] = obj["content_range"]

    def _iter():
        for chunk in obj["body"].iter_chunks(chunk_size=256 * 1024):
            yield chunk

    return StreamingResponse(
        _iter(), status_code=obj["status"], media_type=obj["content_type"], headers=headers
    )


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse, summary="전사(화자별 세그먼트)")
async def get_transcript(meeting_id: str, user: User = Depends(get_current_user)):
    await _get_owned_meeting(meeting_id, user)
    segments = await meeting_service.get_segments(meeting_id)
    return TranscriptResponse(
        meeting_id=meeting_id,
        segments=[
            SegmentResponse(
                seq=s.seq,
                speaker_label=s.speaker_label,
                speaker_name=s.speaker_name,
                start_ms=s.start_ms,
                end_ms=s.end_ms,
                text=s.text,
            )
            for s in segments
        ],
    )


@router.patch("/{meeting_id}/speakers", summary="화자 라벨 → 실명 매핑")
async def update_speakers(
    meeting_id: str, body: SpeakerMappingRequest, user: User = Depends(get_current_user)
):
    await _get_owned_meeting(meeting_id, user)
    await meeting_service.update_speaker_names(meeting_id, body.mapping)
    return {"message": "화자 매핑이 저장되었습니다."}


@router.patch("/{meeting_id}/minutes", response_model=MinutesResponse, summary="회의록 수동 편집")
async def update_minutes(
    meeting_id: str, body: UpdateMinutesRequest, user: User = Depends(get_current_user)
):
    meeting = await _get_owned_meeting(meeting_id, user)
    summary = body.summary if body.summary is not None else body.content.get("summary", "")
    row = await meeting_service.save_minutes(
        meeting_id, summary=summary, content=body.content, model_used="manual"
    )
    return MinutesResponse(
        summary=row.summary,
        content=body.content,
        model_used=row.model_used,
        version=row.version,
    )


@router.post("/{meeting_id}/regenerate", response_model=MinutesResponse, summary="회의록 재생성")
async def regenerate_minutes(meeting_id: str, user: User = Depends(get_current_user)):
    meeting = await _get_owned_meeting(meeting_id, user)
    if meeting.status not in (MeetingStatus.COMPLETED, MeetingStatus.TRANSCRIBED):
        raise HTTPException(status_code=409, detail="전사가 완료된 후에 재생성할 수 있습니다.")
    row = await meeting_service.regenerate_minutes(meeting_id)
    if row is None:
        raise HTTPException(status_code=400, detail="재생성할 전사 내용이 없습니다.")
    try:
        content = json.loads(row.content_json)
    except (ValueError, TypeError):
        content = {}
    return MinutesResponse(
        summary=row.summary, content=content, model_used=row.model_used, version=row.version
    )


@router.post("/{meeting_id}/publish", response_model=PublishResponse, summary="회의록을 아티펙트로 발행")
async def publish_meeting(meeting_id: str, user: User = Depends(get_current_user)):
    meeting = await _get_owned_meeting(meeting_id, user)
    result = await meeting_service.publish_to_artifact(meeting)
    if result is None:
        raise HTTPException(status_code=400, detail="발행할 회의록이 없습니다.")
    return PublishResponse(public_token=result["public_token"], artifact_id=result["artifact_id"])


@router.delete("/{meeting_id}", summary="회의 삭제")
async def delete_meeting(meeting_id: str, user: User = Depends(get_current_user)):
    meeting = await _get_owned_meeting(meeting_id, user)
    await meeting_service.delete_meeting(meeting)
    return {"message": "회의가 삭제되었습니다."}
