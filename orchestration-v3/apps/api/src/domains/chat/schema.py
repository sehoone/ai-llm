"""chat 도메인 DTO (ADR-0008)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.domains.chat.model import ChatAttachment, ChatMessage, ChatSession

# 지원 첨부 타입 — 이미지는 비전(ADR-0014), 단순 텍스트는 인라인 디코드,
# 문서(PDF·Office)는 engine/extraction으로 본문 추출(ADR-0016).
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
SUPPORTED_TEXT_TYPES = {"text/plain", "text/markdown", "text/csv", "application/json"}
SUPPORTED_DOC_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
}
ALL_SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_TEXT_TYPES | SUPPORTED_DOC_TYPES
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class FileAttachment(BaseModel):
    """실시간 전송용 첨부 (base64)."""

    filename: str
    content_type: str
    data: str  # base64


class AttachmentMeta(BaseModel):
    """이력 조회용 첨부 메타 (바이트 미포함)."""

    id: int
    filename: str
    content_type: str
    file_size: int

    @classmethod
    def from_model(cls, a: ChatAttachment) -> "AttachmentMeta":
        return cls(id=a.id, filename=a.filename, content_type=a.content_type, file_size=a.file_size)


class SessionCreateRequest(BaseModel):
    title: str | None = None


class SessionRenameRequest(BaseModel):
    title: str = Field(min_length=1)


class SessionResponse(BaseModel):
    id: int
    title: str

    @classmethod
    def from_model(cls, s: ChatSession) -> "SessionResponse":
        return cls(id=s.id, title=s.title)


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    attachments: list[AttachmentMeta] | None = None

    @classmethod
    def from_model(
        cls, m: ChatMessage, attachments: list[ChatAttachment] | None = None
    ) -> "MessageResponse":
        return cls(
            id=m.id,
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls,
            attachments=[AttachmentMeta.from_model(a) for a in attachments] if attachments else None,
        )


class MessageRequest(BaseModel):
    content: str = Field(min_length=1)
    # 선택: 이 요청에 사용할 chat 리소스(미지정 시 기본 모델) — ADR-0011 §4.
    llm_resource_id: int | None = None
    # 선택: 지식베이스 그룹 — 지정 시 검색 컨텍스트를 사전 주입 (ADR-0012 §1).
    rag_group: str | None = None
    # 선택: 첨부 파일 (base64, 이미지는 비전) — ADR-0014.
    files: list[FileAttachment] | None = None


class ApprovalDecision(BaseModel):
    tool_call_id: str
    approved: bool
    # allow_edit 도구에 한해 수정된 인자(선택).
    args: dict[str, Any] | None = None


class ApprovalResumeRequest(BaseModel):
    group_key: str
    decisions: list[ApprovalDecision] = Field(min_length=1)
