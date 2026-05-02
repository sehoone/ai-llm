"""LangGraph Agent — orchestrates the LLM workflow and streaming responses."""

import asyncio
from typing import AsyncGenerator, Optional
from urllib.parse import quote_plus

from asgiref.sync import sync_to_async
from langchain_core.messages import BaseMessage, convert_to_openai_messages
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from psycopg_pool import AsyncConnectionPool

from src.common.config import Environment, settings
from src.common.langgraph._memory import MemoryMixin
from src.common.langgraph._nodes import NodesMixin
from src.common.langgraph.tools import tools
from src.common.logging import logger
from src.common.metrics import langgraph_checkpointer_failures_total
from src.common.schemas.graph import GraphState
from src.chatbot.schemas.chat_schema import Message
from src.common.services.graph import dump_messages
from src.common.services.llm import LLMService

def _get_langfuse_callbacks():
    if settings.langfuse_is_enabled:
        from langfuse.langchain import CallbackHandler
        return [CallbackHandler()]
    return []


class LangGraphAgent(MemoryMixin, NodesMixin):
    """Stateful LangGraph agent with long-term memory and tool support.

    Graph topology (per turn):
        START → [think → verify →] chat → [tool_call →] chat → END
    """

    def __init__(self):
        self.llm_service = LLMService()
        self.llm_service.bind_tools(tools)
        self.tools_by_name = {tool.name: tool for tool in tools}
        self._connection_pool: Optional[AsyncConnectionPool] = None
        self._graph: Optional[CompiledStateGraph] = None
        self.memory = None  # lazily initialised by MemoryMixin
        logger.info(
            "langgraph_agent_initialized",
            model=settings.DEFAULT_LLM_MODEL,
            environment=settings.ENVIRONMENT.value,
        )

    # ── Infrastructure ────────────────────────────────────────────────────────

    async def _get_connection_pool(self) -> Optional[AsyncConnectionPool]:
        """AsyncPostgresSaver용 연결 풀. 최초 호출 시 생성 후 재사용.

        Returns:
            Optional[AsyncConnectionPool]: The pool, or None in production if creation fails.

        Raises:
            Exception: In non-production environments if pool creation fails.
        """
        if self._connection_pool is None:
            try:
                connection_url = (
                    "postgresql://"
                    f"{quote_plus(settings.POSTGRES_USER)}:{quote_plus(settings.POSTGRES_PASSWORD)}"
                    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
                )
                self._connection_pool = AsyncConnectionPool(
                    connection_url,
                    open=False,
                    max_size=settings.POSTGRES_POOL_SIZE,
                    # autocommit: checkpoint마다 즉시 커밋
                    # prepare_threshold=None: pgbouncer 호환 (prepared statement 비활성화)
                    kwargs={"autocommit": True, "connect_timeout": 5, "prepare_threshold": None},
                )
                await self._connection_pool.open()
                logger.info(
                    "connection_pool_created",
                    max_size=settings.POSTGRES_POOL_SIZE,
                    environment=settings.ENVIRONMENT.value,
                )
            except Exception as e:
                logger.error("connection_pool_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    langgraph_checkpointer_failures_total.inc()
                    logger.critical(
                        "checkpointer_unavailable_degraded_mode",
                        note="conversation history will not persist across restarts",
                    )
                    return None
                raise
        return self._connection_pool

    async def create_graph(self) -> Optional[CompiledStateGraph]:
        """LangGraph 워크플로 빌드 및 컴파일 (idempotent).

        Checkpoint:
        - 각 노드 완료 시 GraphState를 PostgreSQL에 자동 저장
        - 식별 키: thread_id (= session_id) — 동일 thread_id 재호출 시 상태 복원
        - setup()이 생성하는 테이블:
            · checkpoints       — 노드별 전체 상태 스냅샷
            · checkpoint_blobs  — 상태 직렬화 데이터
            · checkpoint_writes — 노드 중간 쓰기 (내결함성용)
        - DB 연결 실패 시 (프로덕션) checkpointer=None → 메모리 유지, 재시작 시 초기화
        """
        if self._graph is None:
            try:
                # 플로우:
                #   일반:        START → chat → END
                #   툴 호출:     START → chat → tool_call → chat → ... → END
                #   딥씽킹:      START → think → chat → END
                builder = StateGraph(GraphState)
                builder.add_node("chat", self._chat, ends=["tool_call", END]) # chat: 메인 LLM 응답 노드. 툴 호출 감지 시 tool_call, 그 외 END
                builder.add_node("tool_call", self._tool_call, ends=["chat"]) # tool_call: 툴 실행 후 항상 chat으로 복귀
                builder.add_node("think", self._think, ends=["chat"]) # think: 응답 전략 수립 (딥씽킹 전용). 항상 chat으로 넘김
                builder.add_conditional_edges(START, self._route_start) # _route_start: is_deep_thinking 또는 질문 복잡도에 따라 think 또는 chat으로 분기

                connection_pool = await self._get_connection_pool()
                if connection_pool:
                    # setup(): 체크포인트 테이블 생성 (이미 존재하면 스킵)
                    checkpointer = AsyncPostgresSaver(connection_pool)
                    await checkpointer.setup()
                else:
                    # 프로덕션: checkpointer 없이 진행 / 그 외: 예외 발생
                    checkpointer = None
                    if settings.ENVIRONMENT != Environment.PRODUCTION:
                        raise RuntimeError("Connection pool initialization failed")

                self._graph = builder.compile(
                    checkpointer=checkpointer,
                    name=f"{settings.PROJECT_NAME} Agent ({settings.ENVIRONMENT.value})",
                )
                logger.info(
                    "graph_created",
                    graph_name=f"{settings.PROJECT_NAME} Agent",
                    environment=settings.ENVIRONMENT.value,
                    has_checkpointer=checkpointer is not None,
                )
            except Exception as e:
                logger.error("graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    langgraph_checkpointer_failures_total.inc()
                    logger.critical(
                        "graph_unavailable_degraded_mode",
                        note="LLM graph failed to initialize; responses will not be served",
                    )
                    return None
                raise
        return self._graph

    # ── Public interface ──────────────────────────────────────────────────────

    async def get_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
        is_deep_thinking: bool = False,
        system_instructions: Optional[str] = None,
        rag_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> list[dict]:
        """Run the graph to completion and return all resulting messages.

        Long-term memory is retrieved before invocation and updated asynchronously afterward.

        Args:
            messages: The conversation messages to process.
            session_id: LangGraph thread ID used for checkpoint persistence.
            user_id: Optional user ID for scoped long-term memory.
            is_deep_thinking: Enable think → verify pre-processing nodes.
            system_instructions: Optional custom system prompt override.
            rag_key: Optional RAG key to inject retrieval context.

        Returns:
            list[dict]: Processed assistant and user messages from the completed run.

        Raises:
            Exception: If the graph invocation fails.
        """
        if self._graph is None:
            self._graph = await self.create_graph()

        config = self._build_config(session_id, user_id)
        relevant_memory = (await self._get_relevant_memory(user_id, messages[-1].content)) or "No relevant memory found."

        try:
            async with asyncio.timeout(settings.GRAPH_RESPONSE_TIMEOUT):
                response = await self._graph.ainvoke(
                    input={
                        "messages": dump_messages(messages),
                        "model_name": model_name,
                        "long_term_memory": relevant_memory,
                        "is_deep_thinking": is_deep_thinking,
                        "system_instructions": system_instructions,
                        "rag_key": rag_key,
                    },
                    config=config,
                )
            task = asyncio.create_task(
                self._update_long_term_memory(
                    user_id, convert_to_openai_messages(response["messages"]), config["metadata"]
                )
            )
            task.add_done_callback(
                lambda t: logger.error("memory_update_failed", error=str(t.exception()), session_id=session_id)
                if not t.cancelled() and t.exception()
                else None
            )
            return self._process_messages(response["messages"])
        except Exception as e:
            logger.error("get_response_failed", session_id=session_id, error=str(e))
            raise

    async def get_stream_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
        is_deep_thinking: bool = False,
        system_instructions: Optional[str] = None,
        rag_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream the graph's token output as an async generator.

        Yields section headers for deep thinking nodes (Analysis, Verification, Answer)
        before the actual content tokens. Long-term memory is updated asynchronously
        after streaming completes.

        Args:
            messages: The conversation messages to process.
            session_id: LangGraph thread ID used for checkpoint persistence.
            user_id: Optional user ID for scoped long-term memory.
            is_deep_thinking: Enable think → verify pre-processing nodes.
            system_instructions: Optional custom system prompt override.
            rag_key: Optional RAG key to inject retrieval context.

        Yields:
            str: Individual content tokens or section header strings.

        Raises:
            Exception: If the stream processing fails.
        """
        if self._graph is None:
            self._graph = await self.create_graph()

        config = self._build_config(session_id, user_id)
        relevant_memory = (await self._get_relevant_memory(user_id, messages[-1].content)) or "No relevant memory found."

        try:
            think_tag_sent = answer_tag_sent = False

            async with asyncio.timeout(settings.GRAPH_RESPONSE_TIMEOUT):
                async for msg, metadata in self._graph.astream(
                    {
                        "messages": dump_messages(messages),
                        "model_name": model_name,
                        "long_term_memory": relevant_memory,
                        "is_deep_thinking": is_deep_thinking,
                        "system_instructions": system_instructions,
                        "rag_key": rag_key,
                    },
                    config,
                    stream_mode="messages",
                ):
                    try:
                        node_name = metadata.get("langgraph_node")
                        if node_name == "think" and not think_tag_sent:
                            yield "[Deep Thinking - Analysis]\n"
                            think_tag_sent = True
                        elif node_name == "chat" and think_tag_sent and not answer_tag_sent:
                            yield "[Deep Thinking - Answer]\n"
                            answer_tag_sent = True
                        yield msg.content
                    except Exception as token_error:
                        logger.error("stream_token_processing_failed", error=str(token_error), session_id=session_id)
                        continue

            state: StateSnapshot = await sync_to_async(self._graph.get_state)(config=config)
            if state.values and "messages" in state.values:
                task = asyncio.create_task(
                    self._update_long_term_memory(
                        user_id, convert_to_openai_messages(state.values["messages"]), config["metadata"]
                    )
                )
                task.add_done_callback(
                    lambda t: logger.error("memory_update_failed", error=str(t.exception()), session_id=session_id)
                    if not t.cancelled() and t.exception()
                    else None
                )
        except Exception as e:
            logger.error("stream_processing_failed", error=str(e), session_id=session_id)
            raise

    async def get_chat_history(self, session_id: str) -> list[Message]:
        """Retrieve the current message state for a session from the checkpoint.

        Args:
            session_id: The LangGraph thread ID.

        Returns:
            list[Message]: Processed messages stored in the checkpoint, or empty list.
        """
        if self._graph is None:
            self._graph = await self.create_graph()
        state: StateSnapshot = await sync_to_async(self._graph.get_state)(
            config={"configurable": {"thread_id": session_id}}
        )
        return self._process_messages(state.values["messages"]) if state.values else []

    async def clear_chat_history(self, session_id: str) -> None:
        """Delete all LangGraph checkpoint rows for a session from PostgreSQL.

        Args:
            session_id: The LangGraph thread ID to clear.

        Raises:
            Exception: If deletion fails for any checkpoint table.
        """
        conn_pool = await self._get_connection_pool()
        if conn_pool is None:
            raise RuntimeError("Connection pool is not available — cannot clear chat history")
        _allowed_tables = set(settings.CHECKPOINT_TABLES)
        try:
            async with conn_pool.connection() as conn:
                for table in settings.CHECKPOINT_TABLES:
                    if table not in _allowed_tables:
                        raise ValueError(f"Refusing to delete from unknown table: {table!r}")
                    try:
                        await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (session_id,))
                        logger.info("checkpoint_table_cleared", table=table, session_id=session_id)
                    except Exception as e:
                        logger.error("checkpoint_table_clear_failed", table=table, error=str(e))
                        raise
        except Exception as e:
            logger.error("clear_chat_history_failed", session_id=session_id, error=str(e))
            raise

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_config(self, session_id: str, user_id: Optional[str]) -> dict:
        """Build the LangGraph run configuration dict.

        Args:
            session_id: Used as the LangGraph ``thread_id`` for checkpoint scoping.
            user_id: Attached to metadata for tracing and memory operations.

        Returns:
            dict: Config with ``configurable``, ``callbacks``, and ``metadata`` keys.
        """
        return {
            "configurable": {"thread_id": session_id},
            "callbacks": _get_langfuse_callbacks(),
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "environment": settings.ENVIRONMENT.value,
                "debug": settings.DEBUG,
            },
        }

    def _process_messages(self, messages: list[BaseMessage]) -> list[Message]:
        """Convert LangChain BaseMessages to API-facing Message objects.

        Filters out non-user/assistant messages, flattens structured content
        blocks to plain text, and skips empty messages.

        Args:
            messages: Raw LangChain messages from the graph state.

        Returns:
            list[Message]: Cleaned messages ready for API responses.
        """
        result = []
        for message in convert_to_openai_messages(messages):
            if message["role"] not in ("assistant", "user") or not message["content"]:
                continue

            content = message["content"]
            if isinstance(content, list):
                text_parts = [
                    block["text"]
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text" and "text" in block
                ] + [block for block in content if isinstance(block, str)]
                content = "\n".join(text_parts)

            if content:
                result.append(Message(role=message["role"], content=str(content)))

        return result
