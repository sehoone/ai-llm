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

_VERIFY_PROMPT = """You are a Critical Reviewer.
Review the analysis and plan provided in the previous turn.

**Guidelines:**
1.  **Critique**: identify any logical gaps, missing edge cases, or potential inaccuracies in the plan.
2.  **Enhancement**: Suggest 1-2 specific ways to make the final answer more insightful or comprehensive.
3.  **Safety**: Ensure no safety guidelines are violated.

**Output Style:**
- Concise and constructive.
- **DO NOT** generate the final answer.
- Focus on *improving* the execution of the plan.
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
        current_llm = self.llm_service.get_llm()
        model_name = (
            current_llm.model_name
            if current_llm and hasattr(current_llm, "model_name")
            else settings.DEFAULT_LLM_MODEL
        )

        if state.system_instructions:
            system_prompt = (
                f"{state.system_instructions}\n\nMemory:\n{state.long_term_memory}"
                if state.long_term_memory
                else state.system_instructions
            )
        else:
            system_prompt = load_system_prompt(long_term_memory=state.long_term_memory)

        messages = prepare_messages(state.messages, current_llm, system_prompt)

        try:
            with llm_inference_duration_seconds.labels(model=model_name).time():
                response_message = await self.llm_service.call(messages)

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
            response = await self.llm_service.call(messages)
            content = _DEEP_THINKING_TAG_RE.sub("", str(response.content))
            response.content = f"[Deep Thinking - Analysis]\n{content}\n\n"
            return Command(update={"messages": [response]}, goto="verify")
        except Exception as e:
            logger.error("think_step_failed", session_id=config["configurable"]["thread_id"], error=str(e))
            return Command(goto="chat")

    async def _verify(self, state: GraphState, config: RunnableConfig) -> Command:
        """Deep thinking verification node — critiques the analysis plan."""
        current_llm = self.llm_service.get_llm()
        messages = prepare_messages(state.messages, current_llm, _VERIFY_PROMPT)

        try:
            response = await self.llm_service.call(messages)
            content = _DEEP_THINKING_TAG_RE.sub("", str(response.content))
            response.content = f"[Deep Thinking - Verification]\n{content}\n\n"
            return Command(update={"messages": [response]}, goto="chat")
        except Exception as e:
            logger.error("verify_step_failed", session_id=config["configurable"]["thread_id"], error=str(e))
            return Command(goto="chat")

    def _route_start(self, state: GraphState) -> str:
        """Conditional entry — routes to 'think' for deep thinking, else 'chat'."""
        return "think" if state.is_deep_thinking else "chat"
