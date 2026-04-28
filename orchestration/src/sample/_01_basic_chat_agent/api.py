"""샘플 01 — 기본 LangGraph 채팅 API

Routes:
    POST /api/v1/sample/basic-chat/chat    — 일반 채팅 (전체 응답)
    POST /api/v1/sample/basic-chat/stream  — 스트리밍 채팅 (SSE)
    GET  /api/v1/sample/basic-chat/history — 대화 히스토리 조회

학습 포인트:
    1. LangGraphAgent는 session_id(=thread_id)로 PostgreSQL에 상태를 저장
    2. 같은 session_id로 요청하면 이전 대화가 자동 복원됨
    3. 스트리밍은 AsyncGenerator → StreamingResponse + SSE 포맷으로 전달
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.chatbot.api.chatbot_api import agent
from src.chatbot.schemas.chat_schema import Message

router = APIRouter()


# ── 스키마 ──────────────────────────────────────────────────────────────────────

class BasicChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    system_instructions: Optional[str] = None


class BasicChatResponse(BaseModel):
    session_id: str
    response: str


# ── 엔드포인트 ──────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=BasicChatResponse,
    summary="기본 채팅",
    description="""
LangGraphAgent를 사용한 기본 채팅 예시.

- `session_id` 없으면 UUID로 새 세션 자동 생성
- 같은 `session_id` 재사용 시 PostgreSQL 체크포인트에서 이전 대화 복원
- `system_instructions`로 에이전트 역할/성격 커스터마이즈 가능

**실제 구현 코드:** `src/chatbot/api/chatbot_api.py`
    """,
)
async def basic_chat(body: BasicChatRequest):
    session_id = body.session_id or str(uuid.uuid4())

    messages = [Message(role="user", content=body.message)]
    result = await agent.get_response(
        messages=messages,
        session_id=session_id,
        system_instructions=body.system_instructions,
    )

    # result는 전체 대화 히스토리, 마지막 assistant 메시지가 현재 응답
    last_assistant = next(
        (m for m in reversed(result) if m.role == "assistant"), None
    )
    if not last_assistant:
        raise HTTPException(status_code=500, detail="에이전트 응답을 받지 못했습니다.")

    return BasicChatResponse(session_id=session_id, response=last_assistant.content)


@router.post(
    "/stream",
    summary="스트리밍 채팅 (SSE)",
    description="""
LangGraphAgent의 스트리밍 응답 예시.

토큰이 생성되는 즉시 SSE(text/event-stream)로 전송됩니다.

**SSE 포맷:**
```
data: 안녕

data: 하세요

data: [DONE]
```

**JavaScript 수신 예시:**
```js
const res = await fetch('/api/v1/sample/basic-chat/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({message: '안녕', session_id: 'my-session'})
});
const reader = res.body.getReader();
// ... reader.read() 루프
```

**실제 구현 코드:** `src/chatbot/api/chatbot_api.py`
    """,
)
async def basic_chat_stream(body: BasicChatRequest):
    session_id = body.session_id or str(uuid.uuid4())
    messages = [Message(role="user", content=body.message)]

    async def event_stream():
        # 첫 청크: session_id 전달
        yield f"data: {{\"session_id\":\"{session_id}\"}}\n\n"

        async for token in agent.get_stream_response(
            messages=messages,
            session_id=session_id,
            system_instructions=body.system_instructions,
        ):
            if token:
                safe = token.replace("\n", "\\n")
                yield f"data: {safe}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/history",
    summary="대화 히스토리 조회",
    description="session_id에 해당하는 PostgreSQL 체크포인트에서 메시지 히스토리를 조회합니다.",
)
async def get_history(session_id: str):
    messages = await agent.get_chat_history(session_id)
    return {
        "session_id": session_id,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }
