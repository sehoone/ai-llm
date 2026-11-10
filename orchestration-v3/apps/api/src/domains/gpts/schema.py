"""gpts 도메인 DTO.

web(V2 기준)이 기대하는 필드명을 유지한다 — `GPTSessionResponse.session_id`,
메시지는 `{role, content}` 평면 쌍. 비스트림 응답은 라우터에서 `ApiResponse[T]`로 감싼다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.domains.gpts.model import CustomGpt, GptSession


# ── CustomGPT CRUD ──
class CustomGptCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    instructions: str = Field(min_length=1)
    is_public: bool = False
    model: str | None = None
    rag_key: str | None = None


class CustomGptUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    instructions: str | None = None
    is_public: bool | None = None
    model: str | None = None


class CustomGptResponse(BaseModel):
    id: str
    user_id: int
    name: str
    description: str | None
    instructions: str
    rag_key: str
    is_public: bool
    model: str

    @classmethod
    def from_model(cls, g: CustomGpt) -> "CustomGptResponse":
        return cls(
            id=g.id,
            user_id=g.user_id,
            name=g.name,
            description=g.description,
            instructions=g.instructions,
            rag_key=g.rag_key,
            is_public=g.is_public,
            model=g.model,
        )


# ── 세션 ──
class GptSessionResponse(BaseModel):
    session_id: str
    name: str
    custom_gpt_id: str

    @classmethod
    def from_model(cls, s: GptSession) -> "GptSessionResponse":
        return cls(session_id=s.id, name=s.name, custom_gpt_id=s.custom_gpt_id)


class SessionRenameRequest(BaseModel):
    name: str = Field(min_length=1)


# ── 메시지 / 채팅 ──
class GptMessage(BaseModel):
    role: str
    content: str


class GptChatHistoryResponse(BaseModel):
    messages: list[GptMessage]


class GptChatRequest(BaseModel):
    session_id: str = Field(..., description="GPT 세션 ID")
    messages: list[GptMessage] = Field(..., min_length=1)
    is_deep_thinking: bool = False
    # 선택: 이 요청에 사용할 chat 리소스(미지정 시 기본 모델) — ADR-0011 §4.
    llm_resource_id: int | None = None
