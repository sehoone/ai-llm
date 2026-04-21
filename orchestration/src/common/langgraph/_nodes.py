"""LangGraph node implementations for LangGraphAgent."""

import json
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

_MAX_VERIFY_ITERATIONS = 2

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

_VERIFY_PROMPT = """You are a strict Quality Evaluator for AI responses.
Evaluate the last assistant message against the user's original request.

**Evaluation criteria:**
1. **Completeness**: Does it fully address every part of the user's question?
2. **Accuracy**: Is the information factually correct and logically sound?
3. **Depth**: Is the explanation sufficiently detailed and insightful?
4. **Clarity**: Is it well-structured and easy to understand?

**Output format (strict JSON, no markdown, no extra text):**
{
  "approved": true,
  "feedback": ""
}
or
{
  "approved": false,
  "feedback": "<concrete, actionable instructions for what must be improved in the next attempt>"
}

Only set approved=true when the response genuinely meets all criteria.
If approved=false, feedback must be specific — not generic like 'improve clarity'.
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

        if state.verify_feedback:
            system_prompt += f"\n\n[Quality Feedback — must address in this response]\n{state.verify_feedback}"

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

            if response_message.tool_calls:
                goto = "tool_call"
            elif state.is_deep_thinking:
                goto = "verify"
            else:
                goto = END
            return Command(update={"messages": [response_message], "verify_feedback": None}, goto=goto)

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
            return Command(update={"messages": [response]}, goto="verify")
        except Exception as e:
            logger.error("think_step_failed", session_id=config["configurable"]["thread_id"], error=str(e))
            return Command(goto="chat")

    async def _verify(self, state: GraphState, config: RunnableConfig) -> Command:
        """Quality evaluation node — approves the response or sends feedback to chat for retry."""
        session_id = config["configurable"]["thread_id"]
        iterations = state.verify_iterations

        if iterations >= _MAX_VERIFY_ITERATIONS:
            logger.info("verify_max_iterations_reached", session_id=session_id, iterations=iterations)
            return Command(update={"verify_iterations": 0, "verify_feedback": None}, goto=END)

        current_llm = self.llm_service.get_llm()
        messages = prepare_messages(state.messages, current_llm, _VERIFY_PROMPT)

        try:
            response = await self.llm_service.call(messages, model_name=state.model_name, config=config)
            raw = _DEEP_THINKING_TAG_RE.sub("", str(response.content)).strip()

            try:
                result = json.loads(raw)
                approved: bool = result.get("approved", True)
                feedback: str = result.get("feedback", "")
            except json.JSONDecodeError:
                logger.warning("verify_json_parse_failed", session_id=session_id, raw=raw[:200])
                approved, feedback = True, ""

            logger.info(
                "verify_quality_evaluated",
                session_id=session_id,
                approved=approved,
                iteration=iterations + 1,
                feedback_preview=feedback[:100] if feedback else "",
            )

            if approved or not feedback:
                return Command(update={"verify_iterations": 0, "verify_feedback": None}, goto=END)

            response.content = f"[Deep Thinking - Verification (attempt {iterations + 1})]\n{feedback}\n\n"
            return Command(
                update={
                    "messages": [response],
                    "verify_feedback": feedback,
                    "verify_iterations": iterations + 1,
                },
                goto="chat",
            )
        except Exception as e:
            logger.error("verify_step_failed", session_id=session_id, error=str(e))
            return Command(update={"verify_iterations": 0, "verify_feedback": None}, goto=END)

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
