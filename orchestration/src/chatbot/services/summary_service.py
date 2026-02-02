
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from src.common.config import settings

# Initialize LLM for summarization (using a fast model)
summary_llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4o-mini", # or a cheaper/faster model like gpt-3.5-turbo
    temperature=0.5,
)

summary_prompt = ChatPromptTemplate.from_template(
    """다음 대화의 첫 번째 사용자 질문과 AI 답변을 바탕으로 3~5단어 정도의 짧고 간결한 대화 주제(제목)를 한국어로 생성해주세요.
    
    사용자: {user_message}
    AI: {ai_message}
    
    제목:"""
)

class ChatSummaryService:
    async def generate_title(self, user_message: str, ai_message: str) -> str:
        """Generates a concise title for the chat session based on the first interaction."""
        try:
            chain = summary_prompt | summary_llm
            response = await chain.ainvoke({
                "user_message": user_message,
                "ai_message": ai_message
            })
            title = response.content.strip().replace('"', '')
            return title
        except Exception as e:
            # Fallback title if generation fails
            return "새로운 대화"

chat_summary_service = ChatSummaryService()
