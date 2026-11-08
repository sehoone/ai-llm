"""meeting 도메인 라우터 — 오디오 업로드·상태 폴링·전사/회의록 조회·발행.

web `src/api/meetings.ts` 계약과 경로·필드 정렬. 응답은 `ApiResponse[T]`로 감싼다(axios 자동
unwrap). 단, `/audio`만 원본 바이트 스트리밍(래퍼 미적용).
"""

from __future__ import annotations

import json

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from src.core.config import settings
from src.core.db import get_session
from src.core.response import ApiResponse
from src.domains.auth.dependencies import get_current_user
from src.domains.meeting.model import MeetingStatus
from src.domains.meeting.schema import (
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
from src.domains.meeting.service import (
    MeetingService,
    audio_content_type,
    meeting_storage,
    run_process_meeting,
)
from src.domains.user.model import User

router = APIRouter()


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes | None:
    """업로드를 메모리로 읽되 한도 초과 시 조기 중단(과대/악의적 업로드 방어)."""
    buf = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            return None
    return bytes(buf)


def _minutes_response(service: MeetingService, meeting_id: str) -> MinutesResponse | None:
    latest = service.get_latest_minutes(meeting_id)
    if latest is None:
        return None
    try:
        content = json.loads(latest.content_json)
    except (ValueError, TypeError):
        content = {}
    return MinutesResponse(
        summary=latest.summary, content=content, model_used=latest.model_used, version=latest.version
    )


@router.post("", response_model=ApiResponse[CreateMeetingResponse])
async def create_meeting(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(default=""),
    language: str = Form(default=""),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[CreateMeetingResponse]:
    """녹음 업로드 → 백그라운드 전사+요약 시작."""
    max_bytes = settings.meeting_max_audio_mb * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"오디오 크기({file.size / (1024 * 1024):.1f}MB)가 한도({settings.meeting_max_audio_mb}MB)를 초과합니다.",
        )
    data = await _read_capped(file, max_bytes)
    if data is None:
        raise HTTPException(status_code=413, detail=f"오디오 크기가 한도({settings.meeting_max_audio_mb}MB)를 초과합니다.")
    if not data:
        raise HTTPException(status_code=400, detail="빈 오디오 파일입니다.")

    meeting = await MeetingService(session).create_meeting(
        user_id=user.id,
        title=title.strip(),
        filename=file.filename or "recording.webm",
        data=data,
        language=(language or settings.meeting_default_locale),
    )
    background_tasks.add_task(run_process_meeting, meeting.id)
    return ApiResponse.ok(CreateMeetingResponse(id=meeting.id, status=meeting.status))


@router.get("", response_model=ApiResponse[MeetingListResponse])
def list_meetings(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[MeetingListResponse]:
    meetings = MeetingService(session).list_meetings(user.id)
    return ApiResponse.ok(MeetingListResponse(items=[MeetingSummary.from_model(m) for m in meetings]))


@router.get("/{meeting_id}", response_model=ApiResponse[MeetingDetailResponse])
def get_meeting(
    meeting_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[MeetingDetailResponse]:
    svc = MeetingService(session)
    meeting = svc.get_owned(meeting_id, user)
    detail = MeetingDetailResponse(
        **MeetingSummary.from_model(meeting).model_dump(), minutes=_minutes_response(svc, meeting_id)
    )
    return ApiResponse.ok(detail)


@router.get("/{meeting_id}/audio")
def get_meeting_audio(
    meeting_id: str,
    download: bool = Query(default=False, description="true면 첨부(다운로드), 기본은 인라인(재생)"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """저장된 오디오를 재생(인라인)/다운로드(첨부)용으로 스트리밍."""
    meeting = MeetingService(session).get_owned(meeting_id, user)
    storage = meeting_storage()
    key = meeting.audio_object_key
    if not storage.exists(key):
        raise HTTPException(status_code=404, detail="오디오 파일을 찾을 수 없습니다.")
    filename = meeting.audio_filename or f"{meeting_id}.audio"
    disposition = f'{"attachment" if download else "inline"}; filename="{filename}"'
    return StreamingResponse(
        storage.open_stream(key),
        media_type=audio_content_type(key),
        headers={"Content-Disposition": disposition, "Accept-Ranges": "bytes"},
    )


@router.get("/{meeting_id}/transcript", response_model=ApiResponse[TranscriptResponse])
def get_transcript(
    meeting_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[TranscriptResponse]:
    svc = MeetingService(session)
    svc.get_owned(meeting_id, user)
    segments = svc.get_segments(meeting_id)
    return ApiResponse.ok(
        TranscriptResponse(
            meeting_id=meeting_id, segments=[SegmentResponse.from_model(s) for s in segments]
        )
    )


@router.patch("/{meeting_id}/speakers", response_model=ApiResponse[dict])
def update_speakers(
    meeting_id: str,
    body: SpeakerMappingRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[dict]:
    svc = MeetingService(session)
    svc.get_owned(meeting_id, user)
    svc.update_speaker_names(meeting_id, body.mapping)
    return ApiResponse.ok({"message": "화자 매핑이 저장되었습니다."})


@router.patch("/{meeting_id}/minutes", response_model=ApiResponse[MinutesResponse])
def update_minutes(
    meeting_id: str,
    body: UpdateMinutesRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiResponse[MinutesResponse]:
    svc = MeetingService(session)
    svc.get_owned(meeting_id, user)
    summary = body.summary if body.summary is not None else body.content.get("summary", "")
    row = svc.save_minutes_manual(meeting_id, summary=summary, content=body.content)
    return ApiResponse.ok(
        MinutesResponse(
            summary=row.summary, content=body.content, model_used=row.model_used, version=row.version
        )
    )


@router.post("/{meeting_id}/regenerate", response_model=ApiResponse[MinutesResponse])
async def regenerate_minutes(
    meeting_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[MinutesResponse]:
    svc = MeetingService(session)
    meeting = svc.get_owned(meeting_id, user)
    if meeting.status not in (MeetingStatus.COMPLETED, MeetingStatus.TRANSCRIBED):
        raise HTTPException(status_code=409, detail="전사가 완료된 후에 재생성할 수 있습니다.")
    row = await svc.regenerate_minutes(meeting_id)
    if row is None:
        raise HTTPException(status_code=400, detail="재생성할 전사 내용이 없습니다.")
    try:
        content = json.loads(row.content_json)
    except (ValueError, TypeError):
        content = {}
    return ApiResponse.ok(
        MinutesResponse(summary=row.summary, content=content, model_used=row.model_used, version=row.version)
    )


@router.post("/{meeting_id}/publish", response_model=ApiResponse[PublishResponse])
def publish_meeting(
    meeting_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[PublishResponse]:
    svc = MeetingService(session)
    meeting = svc.get_owned(meeting_id, user)
    result = svc.publish_to_artifact(meeting)
    if result is None:
        raise HTTPException(status_code=400, detail="발행할 회의록이 없습니다.")
    return ApiResponse.ok(
        PublishResponse(public_token=result["public_token"], artifact_id=result["artifact_id"])
    )


@router.delete("/{meeting_id}", response_model=ApiResponse[dict])
def delete_meeting(
    meeting_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> ApiResponse[dict]:
    svc = MeetingService(session)
    meeting = svc.get_owned(meeting_id, user)
    svc.delete_meeting(meeting)
    return ApiResponse.ok({"message": "회의가 삭제되었습니다."})
