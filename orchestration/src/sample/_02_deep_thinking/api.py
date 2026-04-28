"""샘플 02 — 딥씽킹 에이전트 API

Routes:
    POST /api/v1/sample/deep-thinking/chat    — 딥씽킹 채팅 (전체 응답)
    POST /api/v1/sample/deep-thinking/stream  — 딥씽킹 스트리밍 (섹션 헤더 포함)

학습 포인트:
    1. is_deep_thinking=True 시 START → think → chat → verify → END 흐름 활성화
    2. think 노드: "답하지 말고 전략만 수립" 지시 → 계획 수립
    3. verify 노드: LLM이 직전 답변을 JSON으로 평가 → approved=False 시 chat 재시도
    4. 스트리밍에서 노드별 섹션 헤더("[Deep Thinking - Analysis]" 등) 포함

복잡한 질문 예시:
    - "마이크로서비스와 모놀리식의 장단점을 비교 분석해주세요"
    - "FastAPI와 Django의 차이점과 선택 기준을 설명해주세요"
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.chatbot.api.chatbot_api import agent
from src.chatbot.schemas.chat_schema import Message

router = APIRouter()


class DeepThinkingRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    is_deep_thinking: bool = True


class DeepThinkingResponse(BaseModel):
    session_id: str
    response: str
    sections: list[str]


@router.post(
    "/chat",
    response_model=DeepThinkingResponse,
    summary="딥씽킹 채팅",
    description="""
think → chat → verify 품질 루프를 활성화한 채팅 예시.

**실행 흐름:**
```
START → think(전략수립) → chat(답변생성) → verify(품질검증)
                                ↑                    │ approved=False
                                └────────────────────┘ (최대 2회 재시도)
```

**응답 구조:**
- `sections`: 각 노드의 출력 구분 (`["Analysis", "Answer", "Verification"]` 등)
- `response`: 최종 assistant 답변

**복잡한 질문을 입력하면 자동으로 딥씽킹 모드가 활성화됩니다:**
(질문 길이 > 300자 또는 "분석", "비교", "설계" 등 키워드 포함 시)

**실제 구현 코드:** `src/common/langgraph/_nodes.py`
    """,
)
async def deep_thinking_chat(body: DeepThinkingRequest):
    session_id = body.session_id or str(uuid.uuid4())
    messages = [Message(role="user", content=body.message)]

    result = await agent.get_response(
        messages=messages,
        session_id=session_id,
        is_deep_thinking=body.is_deep_thinking,
    )

    # 섹션 태그 파싱
    sections = []
    final_response = ""
    for m in result:
        if m.role == "assistant":
            content = m.content
            if "[Deep Thinking - Analysis]" in content:
                sections.append("Analysis")
            elif "[Deep Thinking - Verification" in content:
                sections.append("Verification")
            elif "[Deep Thinking - Answer]" in content:
                sections.append("Answer")
                # [Deep Thinking - Answer]\n 이후 부분이 실제 답변
                final_response = content.replace("[Deep Thinking - Answer]", "").strip()

    if not final_response:
        last = next((m for m in reversed(result) if m.role == "assistant"), None)
        if last:
            final_response = last.content

    if not final_response:
        raise HTTPException(status_code=500, detail="에이전트 응답을 받지 못했습니다.")

    return DeepThinkingResponse(
        session_id=session_id,
        response=final_response,
        sections=sections,
    )


@router.post(
    "/stream",
    summary="딥씽킹 스트리밍 (섹션 헤더 포함)",
    description="""
딥씽킹 모드 스트리밍 — 노드별 섹션 헤더가 포함된 SSE 스트림.

**SSE 이벤트 예시:**
```
event: section
data: {"section": "analysis"}

data: 질문을 분석합니다...

event: section
data: {"section": "answer"}

data: 최종 답변: ...

data: [DONE]
```

**실제 구현 코드:** `src/common/langgraph/graph.py` `get_stream_response()`
    """,
)
async def deep_thinking_stream(body: DeepThinkingRequest):
    session_id = body.session_id or str(uuid.uuid4())
    messages = [Message(role="user", content=body.message)]

    async def event_stream():
        import json
        yield f"data: {{\"session_id\":\"{session_id}\"}}\n\n"

        current_section = None

        async for token in agent.get_stream_response(
            messages=messages,
            session_id=session_id,
            is_deep_thinking=body.is_deep_thinking,
        ):
            if not token:
                continue

            # 섹션 헤더 감지 → event: section 이벤트로 전달
            if "[Deep Thinking - Analysis]" in token:
                yield f"event: section\ndata: {json.dumps({'section': 'analysis'})}\n\n"
                current_section = "analysis"
                continue
            if "[Deep Thinking - Verification" in token:
                yield f"event: section\ndata: {json.dumps({'section': 'verification'})}\n\n"
                current_section = "verification"
                continue
            if "[Deep Thinking - Answer]" in token:
                yield f"event: section\ndata: {json.dumps({'section': 'answer'})}\n\n"
                current_section = "answer"
                continue

            safe = token.replace("\n", "\\n")
            yield f"data: {safe}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
