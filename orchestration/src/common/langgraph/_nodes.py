"""LangGraph node implementations for LangGraphAgent."""

import re

from langchain_core.messages import ToolMessage
from langgraph.graph import END
from langgraph.graph.state import Command
from langgraph.types import RunnableConfig

from src.common.config import settings
from src.common.logging import logger
from src.common.metrics import llm_inference_duration_seconds
from src.common.prompts import load_system_prompt
from src.common.schemas.graph import GraphState
from src.common.services.graph import prepare_messages, process_llm_response

_THINKING_PROMPT = """You are an expert AI strategist designed to ensure high-quality responses.
Your task is NOT to answer the user's question directly, but to ANALYZE the request and PLAN the best possible response.

**Guidelines:**
1.  **Deconstruct**: Break down the user's request into core components and implicit intent.
2.  **Context Expansion**: What background knowledge or context is necessary to give a "Deep" answer?
3.  **Strategy**: Outline a logical structure for the final response (e.g., Introduction -> Core Concept -> Examples -> deep usage -> Conclusion).
4.  **Tone & Style**: Determine the appropriate tone (academic, practical, simple, etc.).

**Output Style:**
- Use **Internal Monologue** (e.g., "The user is asking about X. I must ensure to cover Y and Z...").
- **DO NOT** address the user directly (No "Here is the plan for you").
- **DO NOT** generate the final answer text. Only the plan.
"""

_DEEP_THINKING_TAG_RE = re.compile(
    r"^[\s\*]*\[Deep Thinking - [^\]]+\][\s\*]*", re.IGNORECASE | re.MULTILINE
)


class NodesMixin:
    """Provides LangGraph node methods for LangGraphAgent.

    Requires ``self.llm_service`` and ``self.tools_by_name`` set by the host class.
    """

    async def _chat(self, state: GraphState, config: RunnableConfig) -> Command:
        """Main chat node — calls the LLM and routes to tool_call or END."""
        model_name = state.model_name or settings.DEFAULT_LLM_MODEL
        current_llm = self.llm_service.get_llm()

        if state.system_instructions:
            system_prompt = (
                f"{state.system_instructions}\n\nMemory:\n{state.long_term_memory}"
                if state.long_term_memory
                else state.system_instructions
            )
        else:
            system_prompt = load_system_prompt(long_term_memory=state.long_term_memory)

        if state.thinking_context:
            system_prompt += f"\n\n[Execution Plan]\n{state.thinking_context}"

        messages = prepare_messages(state.messages, current_llm, system_prompt)

        try:
            with llm_inference_duration_seconds.labels(model=model_name).time():
                response_message = await self.llm_service.call(messages, model_name=state.model_name, config=config)

            response_message = process_llm_response(response_message)

            if state.is_deep_thinking:
                response_message.content = f"[Deep Thinking - Answer]\n{response_message.content}"

            logger.info(
                "llm_response_generated",
                session_id=config["configurable"]["thread_id"],
                model=model_name,
                environment=settings.ENVIRONMENT.value,
            )

            goto = "tool_call" if response_message.tool_calls else END
            return Command(update={"messages": [response_message]}, goto=goto)

        except Exception as e:
            logger.error(
                "llm_call_failed_all_models",
                session_id=config["configurable"]["thread_id"],
                error=str(e),
                environment=settings.ENVIRONMENT.value,
            )
            raise Exception(f"failed to get llm response after trying all models: {str(e)}")

    async def _tool_call(self, state: GraphState) -> Command:
        """Tool execution node — runs each tool call from the last message."""
        outputs = []
        for tool_call in state.messages[-1].tool_calls:
            tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
            outputs.append(
                ToolMessage(
                    content=tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return Command(update={"messages": outputs}, goto="chat")

    async def _think(self, state: GraphState, config: RunnableConfig) -> Command:
        """Deep thinking analysis node — plans the response strategy."""
        current_llm = self.llm_service.get_llm()
        messages = prepare_messages(state.messages, current_llm, _THINKING_PROMPT)

        try:
            response = await self.llm_service.call(messages, model_name=state.model_name, config=config)
            content = _DEEP_THINKING_TAG_RE.sub("", str(response.content))
            response.content = f"[Deep Thinking - Analysis]\n{content}\n\n"
            return Command(update={"messages": [response], "thinking_context": content}, goto="chat")
        except Exception as e:
            logger.error("think_step_failed", session_id=config["configurable"]["thread_id"], error=str(e))
            return Command(goto="chat")

    def _route_start(self, state: GraphState) -> str:
        """Conditional entry — routes to 'think' for deep thinking, else 'chat'.

        Auto-routes to 'think' when the last user message is complex,
        even if is_deep_thinking is False.
        """
        if state.is_deep_thinking:
            return "think"
        if state.messages:
            last_content = state.messages[-1].content if hasattr(state.messages[-1], "content") else ""
            if isinstance(last_content, str) and self._is_complex_query(last_content):
                return "think"
        return "chat"

    @staticmethod
    def _is_complex_query(text: str) -> bool:
        """Return True if the query warrants deep thinking based on length or keywords."""
        if len(text) > 300:
            return True
        _COMPLEX_KEYWORDS = (
            # 한국어
            "분석", "비교", "설계", "아키텍처", "왜", "이유", "원인", "차이", "장단점",
            "전략", "구조", "최적화", "개선", "평가", "검토", "추천", "제안",
            # 영어
            "analyze", "analyse", "compare", "design", "architecture", "why", "reason",
            "difference", "pros and cons", "trade-off", "tradeoff", "optimize",
            "improve", "evaluate", "review", "recommend", "suggest", "explain",
        )
        lower = text.lower()
        return any(kw in lower for kw in _COMPLEX_KEYWORDS)
