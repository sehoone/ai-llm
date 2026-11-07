"""chat 도메인 DTO (ADR-0008)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.domains.chat.model import ChatMessage, ChatSession


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

    @classmethod
    def from_model(cls, m: ChatMessage) -> "MessageResponse":
        return cls(id=m.id, role=m.role, content=m.content, tool_calls=m.tool_calls)


class MessageRequest(BaseModel):
    content: str = Field(min_length=1)
    # 선택: 이 요청에 사용할 chat 리소스(미지정 시 기본 모델) — ADR-0011 §4.
    llm_resource_id: int | None = None
    # 선택: 지식베이스 그룹 — 지정 시 검색 컨텍스트를 사전 주입 (ADR-0012 §1).
    rag_group: str | None = None


class ApprovalDecision(BaseModel):
    tool_call_id: str
    approved: bool
    # allow_edit 도구에 한해 수정된 인자(선택).
    args: dict[str, Any] | None = None


class ApprovalResumeRequest(BaseModel):
    group_key: str
    decisions: list[ApprovalDecision] = Field(min_length=1)
