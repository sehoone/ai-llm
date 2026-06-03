"""샘플 01: 기본 LangGraph 채팅 에이전트

실제 구현: src/common/langgraph/graph.py

핵심 개념:
- StateGraph: 노드(함수) + 엣지(흐름)로 정의되는 대화 상태 기계
- GraphState: 각 노드 간에 공유되는 상태 (메시지 목록 포함)
- Checkpoint: 세션 ID(thread_id)를 키로 PostgreSQL에 대화 상태 자동 저장
  → 재시작 후에도 이전 대화 복원 가능
- 스트리밍: astream()으로 토큰 단위 실시간 응답

실제 코드와의 차이점:
- MemoryMixin (long-term memory), NodesMixin(검증 루프) 제거하여 단순화
- LLMService 대신 직접 ChatOpenAI 사용
- 에러 처리, Langfuse 콜백, 프로덕션 예외 처리 생략
"""

import asyncio
from typing import AsyncGenerator, Optional
from urllib.parse import quote_plus

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import RunnableConfig
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, Field
from typing import Annotated


# ── 상태 정의 ──────────────────────────────────────────────────────────────────

class ChatState(BaseModel):
    """LangGraph 노드들이 공유하는 대화 상태.

    messages 필드의 add_messages annotation이 핵심:
    - 일반 필드: 새 값이 이전 값을 완전히 교체
    - add_messages: 새 메시지가 기존 메시지 목록에 추가(append)됨
    - 이로 인해 각 노드가 독립적으로 메시지를 추가해도 안전하게 병합됨
    """

    messages: Annotated[list, add_messages] = Field(default_factory=list)
    system_instructions: Optional[str] = Field(default=None)


# ── 노드 구현 ──────────────────────────────────────────────────────────────────

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


async def chat_node(state: ChatState, config: RunnableConfig) -> dict:
    """메인 LLM 응답 노드.

    state.messages에서 대화 히스토리를 읽고, LLM을 호출한 후
    응답 메시지를 반환한다. 반환된 dict의 key는 GraphState 필드명과 일치해야 한다.

    LangGraph가 반환값을 GraphState에 자동 병합:
    - messages: add_messages reducer가 기존 목록에 새 메시지를 추가
    """
    system_prompt = state.system_instructions or "당신은 친절한 AI 어시스턴트입니다."

    messages = [SystemMessage(content=system_prompt)] + list(state.messages)
    response = await llm.ainvoke(messages, config=config)

    return {"messages": [response]}


# ── 그래프 빌드 ────────────────────────────────────────────────────────────────

class SimpleChatAgent:
    """PostgreSQL 체크포인트를 사용하는 단순 채팅 에이전트."""

    def __init__(self, postgres_url: str):
        self._postgres_url = postgres_url
        self._pool: Optional[AsyncConnectionPool] = None
        self._graph = None

    async def initialize(self):
        """연결 풀과 그래프를 초기화한다. 앱 시작 시 1회 호출."""
        self._pool = AsyncConnectionPool(
            self._postgres_url,
            open=False,
            max_size=10,
            # autocommit=True: 각 체크포인트마다 즉시 커밋
            # prepare_threshold=None: pgbouncer 호환 (prepared statement 비활성화)
            kwargs={"autocommit": True, "prepare_threshold": None},
        )
        await self._pool.open()

        # 체크포인터: thread_id별로 GraphState를 PostgreSQL에 저장
        # setup()은 필요한 테이블(checkpoints, checkpoint_blobs, checkpoint_writes)을 생성
        checkpointer = AsyncPostgresSaver(self._pool)
        await checkpointer.setup()

        # 그래프 정의
        # START → chat → END (기본 단일 노드 구조)
        builder = StateGraph(ChatState)
        builder.add_node("chat", chat_node)
        builder.add_edge(START, "chat")
        builder.add_edge("chat", END)

        self._graph = builder.compile(checkpointer=checkpointer)

    async def chat(
        self,
        user_message: str,
        session_id: str,
        system_instructions: Optional[str] = None,
    ) -> str:
        """단일 메시지를 보내고 전체 응답을 반환한다.

        session_id = LangGraph의 thread_id
        - 같은 session_id를 사용하면 이전 대화가 PostgreSQL에서 자동 복원됨
        - 다른 session_id를 사용하면 새 대화 시작
        """
        config = {"configurable": {"thread_id": session_id}}

        result = await self._graph.ainvoke(
            input={
                "messages": [HumanMessage(content=user_message)],
                "system_instructions": system_instructions,
            },
            config=config,
        )

        # result["messages"]는 전체 대화 히스토리 (새 메시지 포함)
        # 마지막 assistant 메시지가 현재 응답
        last_message = result["messages"][-1]
        return str(last_message.content)

    async def stream_chat(
        self,
        user_message: str,
        session_id: str,
        system_instructions: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """스트리밍 응답 — 토큰 단위로 즉시 yield.

        astream()의 stream_mode="messages":
        - 각 토큰이 나올 때마다 (msg, metadata) 튜플을 yield
        - metadata["langgraph_node"]: 어느 노드에서 나온 토큰인지 식별 가능
        """
        config = {"configurable": {"thread_id": session_id}}

        async for msg, metadata in self._graph.astream(
            input={
                "messages": [HumanMessage(content=user_message)],
                "system_instructions": system_instructions,
            },
            config=config,
            stream_mode="messages",
        ):
            # AIMessageChunk만 yield (ToolMessage, HumanMessage 등 제외)
            if hasattr(msg, "content") and msg.content:
                yield msg.content

    async def close(self):
        """앱 종료 시 연결 풀 정리."""
        if self._pool:
            await self._pool.close()


# ── 실행 예제 ──────────────────────────────────────────────────────────────────

async def main():
    """사용 예시 — 실제 실행 시 PostgreSQL이 필요합니다."""
    import os

    db_url = (
        f"postgresql://{quote_plus(os.getenv('POSTGRES_USER', 'postgres'))}"
        f":{quote_plus(os.getenv('POSTGRES_PASSWORD', 'password'))}"
        f"@{os.getenv('POSTGRES_HOST', 'localhost')}"
        f":5432/{os.getenv('POSTGRES_DB', 'llmonl')}"
    )

    agent = SimpleChatAgent(postgres_url=db_url)
    await agent.initialize()

    session_id = "sample-session-001"

    # 첫 번째 메시지
    response = await agent.chat("안녕하세요!", session_id=session_id)
    print(f"응답: {response}")

    # 두 번째 메시지 — 같은 session_id이므로 이전 대화 기억
    response = await agent.chat("제 이름을 기억하세요? 저는 김개발자입니다.", session_id=session_id)
    print(f"응답: {response}")

    # 스트리밍 예시
    print("스트리밍 응답: ", end="", flush=True)
    async for token in agent.stream_chat("스트리밍 테스트입니다.", session_id=session_id):
        print(token, end="", flush=True)
    print()

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
