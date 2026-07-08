
from langchain_core.messages import HumanMessage, SystemMessage

from src.common.logging import logger
from src.common.services.llm import LLMService

_SYSTEM_PROMPT = (
    "You are a concise title generator. "
    "Given a conversation excerpt, produce a short Korean title (3–5 words). "
    "Output only the title — no quotes, no punctuation, no explanation."
)

_llm_service = LLMService()


class ChatSummaryService:
    async def generate_title(self, user_message: str, ai_message: str) -> str:
        """Generates a concise title for the chat session based on the first interaction."""
        try:
            messages = [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=f"사용자: {user_message}\nAI: {ai_message}\n\n제목:"),
            ]
            response = await _llm_service.call(messages, use_tools=False)
            title = response.content.strip().replace('"', '').replace("'", '')
            return title or "새로운 대화"
        except Exception as e:
            logger.error("title_generation_failed", error=str(e))
            return "새로운 대화"


chat_summary_service = ChatSummaryService()
