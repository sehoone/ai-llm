"""샘플 05: FastAPI SSE 스트리밍 패턴

실제 구현: src/chatbot/api/chatbot_api.py, src/agent/api/agent_api.py

핵심 개념:
- SSE(Server-Sent Events): 단방향 서버→클라이언트 실시간 스트리밍
  - 포맷: "data: <내용>\n\n" (빈 줄 2개가 이벤트 구분자)
  - 이벤트 타입: "event: <type>\ndata: <내용>\n\n"
- StreamingResponse: FastAPI에서 AsyncGenerator를 HTTP 스트림으로 전송
- LangGraph astream(): 토큰 단위 스트리밍을 AsyncGenerator로 소비
- 에러 처리: 스트림 중간 오류를 클라이언트에 알리는 error 이벤트
"""

import asyncio
import json
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Streaming Patterns")


# ── SSE 헬퍼 ──────────────────────────────────────────────────────────────────

def sse_event(data: str, event_type: Optional[str] = None) -> str:
    """SSE 이벤트 문자열 생성.

    표준 SSE 포맷:
      event: <type>   (선택)
      data: <내용>
                      (빈 줄 — 이벤트 끝)

    클라이언트에서:
      eventSource.addEventListener('token', (e) => console.log(e.data))
      eventSource.addEventListener('done', () => console.log('완료'))
      eventSource.addEventListener('error', (e) => console.error(e.data))
    """
    lines = []
    if event_type:
        lines.append(f"event: {event_type}")
    # 줄바꿈 문자는 SSE 이벤트 구분자를 깨므로 이스케이프
    safe_data = data.replace("\n", "\\n")
    lines.append(f"data: {safe_data}")
    lines.append("")  # 빈 줄 (이벤트 종료)
    return "\n".join(lines) + "\n"


def sse_json(payload: dict, event_type: Optional[str] = None) -> str:
    """dict를 JSON으로 직렬화하여 SSE 이벤트로 변환."""
    return sse_event(json.dumps(payload, ensure_ascii=False), event_type)


# ── 스키마 ──────────────────────────────────────────────────────────────────────

class StreamRequest(BaseModel):
    message: str
    session_id: str = "default"


# ── 스트리밍 생성기 패턴 ───────────────────────────────────────────────────────

async def _llm_token_generator(message: str) -> AsyncGenerator[str, None]:
    """LLM 토큰 스트리밍 시뮬레이터.

    실제 코드에서는:
        async for token in agent.get_stream_response(...):
            yield sse_event(token)
    """
    words = f"안녕하세요! '{message}'에 대한 답변입니다. ".split()
    for word in words:
        await asyncio.sleep(0.05)  # LLM 토큰 생성 지연 시뮬레이션
        yield word + " "


async def chat_stream_generator(
    message: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """채팅 스트리밍 SSE 이벤트 생성기.

    이벤트 타입:
    - "start": 스트림 시작, session_id 전달
    - "token": 토큰 청크
    - "done": 스트림 완료 신호
    - "error": 오류 발생 (스트림 중간에도 클라이언트에 알림)

    실제 코드 패턴 (src/agent/api/agent_api.py):
        async for token in agent_instance.get_stream_response(...):
            yield sse_event(token, "token")
        yield sse_event("[DONE]", "done")
    """
    # 시작 이벤트: 클라이언트가 session_id를 알 수 있도록
    yield sse_json({"session_id": session_id, "status": "started"}, event_type="start")

    full_response = []
    try:
        async for token in _llm_token_generator(message):
            full_response.append(token)
            yield sse_event(token, event_type="token")

        # 완료 이벤트: 전체 응답 텍스트도 함께 전달
        yield sse_json(
            {"full_response": "".join(full_response), "status": "done"},
            event_type="done",
        )

    except Exception as e:
        # 스트림 중간 오류: 클라이언트가 정상 종료와 구분할 수 있도록
        yield sse_json({"error": str(e), "status": "error"}, event_type="error")
        raise


# ── 딥씽킹 스트리밍 패턴 ───────────────────────────────────────────────────────

async def deep_thinking_stream_generator(
    message: str,
) -> AsyncGenerator[str, None]:
    """딥씽킹 모드 스트리밍 — 노드별 섹션 헤더 포함.

    실제 코드 (src/common/langgraph/graph.py get_stream_response):
        node_name = metadata.get("langgraph_node")
        if node_name == "think" and not think_tag_sent:
            yield "[Deep Thinking - Analysis]\\n"
        elif node_name == "verify" and not verify_tag_sent:
            yield "[Deep Thinking - Verification]\\n"
        elif node_name == "chat" and not answer_tag_sent:
            yield "[Deep Thinking - Answer]\\n"
        yield msg.content
    """
    think_sent = False
    verify_sent = False
    answer_sent = False

    # think 노드 스트리밍 시뮬레이션
    if not think_sent:
        yield sse_json({"section": "analysis", "content": "[Deep Thinking - Analysis]\n"}, "section")
        think_sent = True

    for token in "질문을 분석합니다. 먼저 X를 다루고 Y로 심화합니다. ".split():
        yield sse_event(token + " ", "token")
        await asyncio.sleep(0.03)

    # verify 노드 스트리밍 시뮬레이션
    if not verify_sent:
        yield sse_json({"section": "verification", "content": "[Deep Thinking - Verification]\n"}, "section")
        verify_sent = True

    for token in "응답 품질을 검증합니다. ".split():
        yield sse_event(token + " ", "token")
        await asyncio.sleep(0.03)

    # chat 노드 최종 답변
    if not answer_sent:
        yield sse_json({"section": "answer", "content": "[Deep Thinking - Answer]\n"}, "section")
        answer_sent = True

    for token in "최종 답변: 요청하신 내용에 대해 상세히 설명드립니다. ".split():
        yield sse_event(token + " ", "token")
        await asyncio.sleep(0.03)

    yield sse_json({"status": "done"}, "done")


# ── 엔드포인트 ──────────────────────────────────────────────────────────────────

@app.post("/stream/chat")
async def stream_chat(request: StreamRequest):
    """기본 채팅 스트리밍 엔드포인트."""
    return StreamingResponse(
        chat_stream_generator(request.message, request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx가 SSE를 버퍼링하지 않도록
        },
    )


@app.post("/stream/deep-thinking")
async def stream_deep_thinking(request: StreamRequest):
    """딥씽킹 모드 스트리밍 — think/verify/chat 노드별 섹션 헤더 포함."""
    return StreamingResponse(
        deep_thinking_stream_generator(request.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


"""
JavaScript 클라이언트 예시:

// POST 방식 SSE (EventSource는 GET만 지원하므로 fetch 사용)
const response = await fetch('/stream/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: '안녕하세요', session_id: 'sess-001' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const events = buffer.split('\\n\\n');
  buffer = events.pop() || '';  // 마지막 불완전한 이벤트는 버퍼에 유지

  for (const event of events) {
    const lines = event.split('\\n');
    const eventType = lines.find(l => l.startsWith('event:'))?.slice(7) || 'message';
    const dataLine = lines.find(l => l.startsWith('data:'))?.slice(6) || '';

    if (eventType === 'token') {
      process.stdout.write(dataLine.replace(/\\\\n/g, '\\n'));
    } else if (eventType === 'done') {
      console.log('\\n완료:', JSON.parse(dataLine));
    } else if (eventType === 'error') {
      console.error('오류:', JSON.parse(dataLine));
    }
  }
}
"""
