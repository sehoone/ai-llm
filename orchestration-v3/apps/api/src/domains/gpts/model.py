"""gpts 도메인 테이블. schema: llmonl. V2 custom_gpt·gpt_session·gpt_chat_message 포팅.

- `custom_gpt`: 사용자 정의 GPT 봇 정의(instructions·rag_key·model).
- `gpt_session`: GPT별 대화 세션.
- `gpt_chat_message`: 세션 내 질문/답변 쌍(간단 Q/A 저장 — chat 도메인의 메시지 모델과 별개).

FK 없음 — 연쇄 정리는 앱(repository)이 명시 수행(chat 도메인 관례와 동일).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


class CustomGpt(SQLModel, table=True):
    __tablename__ = "custom_gpt"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: int = Field(index=True)
    name: str
    description: str | None = Field(default=None)
    instructions: str = Field(default="")
    rag_key: str = Field(default_factory=_uuid, index=True)
    is_public: bool = Field(default=False)
    model: str = Field(default="gpt-4o-mini")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    updated_at: NaiveDatetime | None = Field(default=None)


class GptSession(SQLModel, table=True):
    __tablename__ = "gpt_session"
    __table_args__ = {"schema": "llmonl"}

    id: str = Field(primary_key=True)
    user_id: int = Field(index=True)
    custom_gpt_id: str = Field(index=True)
    name: str = Field(default="")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class GptChatMessage(SQLModel, table=True):
    __tablename__ = "gpt_chat_message"
    __table_args__ = {"schema": "llmonl"}

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    question: str = Field(default="")
    answer: str = Field(default="")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
