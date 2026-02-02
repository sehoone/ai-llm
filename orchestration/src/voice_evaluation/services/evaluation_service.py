"""Evaluation service for voice conversation.

This module provides services for evaluating voice conversations, including
generating responses using LLM, assessing pronunciation, and evaluating
language proficiency.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import List, Dict, Any, TypedDict, Annotated, Optional
import json
import asyncio

from src.common.config import settings
from src.common.logging import logger
from src.voice_evaluation.services.audio_service import AudioService

class ConversationState(TypedDict):
    """Configuration for conversation state."""
    messages: Annotated[List[Dict[str, str]], "List of conversation messages"]
    user_input: str
    assistant_response: str
    evaluation_result: Dict[str, Any]
    audio_data: Optional[bytes]
    pronunciation_result: Optional[Dict[str, Any]]


class EvaluationService:
    """Service for evaluating English language proficiency."""

    def __init__(self):
        """Initialize evaluation service."""
        self.llm = ChatOpenAI(
            model=settings.DEFAULT_LLM_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        self.memory = MemorySaver()
        self.audio_service = AudioService()
        self._setup_prompts()
        self._setup_graph()
    
    def _setup_prompts(self):
        """Set up evaluation and conversation prompts."""
        self.evaluation_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 영어 언어 능력 평가 전문가입니다. 사용자는 영어로 답을 합니다. 사용자의 대화 내용을 분석하여 다음 항목을 평가해주세요:

1. Comprehension (이해도) (0-100점)
2. Fluency (유창성) (0-100점)
3. Grammar (문법) (0-100점)
4. Vocabulary (어휘) (0-100점)

평가 결과는 JSON 형식으로 반환해주세요:
{{
    "grammar_score": 점수 (0-100),
    "vocabulary_score": 점수 (0-100),
    "fluency_score": 점수 (0-100),
    "communication_score": 점수 (0-100),
    "comprehension_score": 점수 (0-100),
    "overall_score": 평균점수 (0-100),
    "feedback": "전체적인 피드백 (2-3 문단으로 상세히 작성)",
    "suggestions": ["개선 제안1", "개선 제안2", ...],
    "strengths": ["강점1", "강점2", ...],
    "weaknesses": ["약점1", "약점2", ...],
    "error_types": {{
        "Past Tense": 비율 (0-100),
        "S-V agreement": 비율 (0-100),
        "Use of Plurals": 비율 (0-100),
        "Others": 비율 (0-100)
    }},
    "corrections": ["구체적인 수정 예시1 (예: 'I had some mail to send' → 'I needed to send some mail')", "구체적인 수정 예시2", ...],
    "category_feedback": {{
        "comprehension": ["Comprehension 관련 피드백1", "Comprehension 관련 피드백2", ...],
        "fluency": ["Fluency 관련 피드백1", "Fluency 관련 피드백2", ...],
        "grammar": ["Grammar 관련 피드백1", "Grammar 관련 피드백2", ...],
        "vocabulary": ["Vocabulary 관련 피드백1", "Vocabulary 관련 피드백2", ...]
    }}
}}

주의사항:
- error_types의 모든 값의 합은 100이 되어야 합니다
- 각 카테고리별 피드백은 2-3개 정도 작성해주세요
- corrections는 실제 대화에서 발견된 오류를 구체적으로 수정 예시와 함께 제공해주세요
- feedback은 상세하고 구체적으로 작성해주세요"""),
            ("human", "다음 대화 내용을 평가해주세요:\n\n{conversation_text}")
        ])
        
        self.conversation_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 영어 언어 능력 모의평가를 진행하는 전문 면접관입니다. 

**역할:**
- 대화가 시작되면 먼저 질문을 제시합니다
- 사용자의 답변을 듣고, 후속 질문이나 새로운 주제로 대화를 이어갑니다
- 자연스럽고 친근한 톤으로 질문하되, 평가 목적을 유지합니다

**질문 주제 예시:**
- 자기소개 및 일상생활
- 취미와 관심사
- 경험과 계획
- 의견 및 선호도
- 가상 상황에 대한 대처

**지침:**
1. 첫 대화에서는 "Hello! Today we will conduct an English language proficiency assessment. Could you please start by briefly introducing yourself?"와 같이 시작합니다
2. 질문은 명확하고 간단하게 영어로 제시합니다
3. 사용자의 답변 수준에 맞춰 질문 난이도를 조절합니다
4. 대화가 자연스럽게 이어지도록 합니다
5. 평가 영역은 5가지로 고정합니다.
Fluency(유창성): 말의 흐름, 끊김/망설임, 속도, 자연스러움
Accuracy(정확성): 문법·표현 오류의 빈도/심각도
Vocabulary(어휘력): 어휘 다양성, 정확한 단어 선택, 수준 적절성
Pronunciation & Intelligibility(발음/명료도): 발음, 강세·억양, 이해 가능성
Coherence(논리/응집성): 답변 구조, 연결어 사용, 내용 전개

6. 각 영역은 0-5점(총 25점)으로 평가합니다.
0: 답변 불가/의사 전달 거의 불가
1: 매우 제한적, 빈번한 오류로 이해 어려움
2: 기본 의사소통 가능하지만 오류/망설임 많음
3: 전반적으로 명확, 중간 수준 오류 존재
4: 자연스럽고 오류 적음, 다양한 표현
5: 매우 자연스러움, 고급 표현/정확성/논리 모두 우수

7. 질문은 레벨을 구분해 단계적으로 진행합니다.
Level 1 (A1-A2): 개인 정보, 일상 루틴, 단순 선호(현재형 중심)
Level 2 (B1): 경험 설명, 이유 제시, 비교(과거형/연결어)
Level 3 (B2): 의견 주장, 장단점, 가설/제안(복합문/추상 주제)
Level 4 (C1+): 시사/사회 문제, 비판적 사고, 반론·재구성
→ 사용자의 이전 답변 점수/난이도 성공 여부에 따라 다음 질문 레벨을 상향 혹은 유지/하향합니다.

8. 한 질문당 최소 2~3개의 follow-up을 준비합니다.
사용자가 짧게 답하면: "Could you tell me more about that?"
이유가 부족하면: "Why do you think so?"
예시가 없으면: "Can you give me an example?"
→ follow-up은 같은 난이도에서 깊이를 늘리는 용도입니다.

9. 답변이 매우 짧거나 회피될 경우 재질문 규칙을 둡니다.
1차: 간단한 되묻기
2차: 선택지 제공("Is it A or B, and why?")
3차: 레벨 한 단계 낮춘 질문으로 전환
→ 사용자가 막히면 **‘실패’가 아니라 ‘조정’**으로 처리합니다.

10. 오류는 즉시 교정하지 말고 ‘기록 후 평가’합니다.
대화 흐름 유지가 최우선.
다만 발음/의미 오해로 진행이 안 될 때만 최소 개입:
"Just to confirm, did you mean … ?"

11. 평가에 필요한 최소 발화량을 확보합니다.
총 대화 시간 1~4분, 또는
사용자의 총 발화가 약 50~300 단어 수준이 되도록 유도합니다.
→ 이 기준 미달이면 "추정치"로 표시합니다.

12. 마지막에는 영역별 피드백 + 총평 + 다음 학습 제안을 제공합니다.
형식 예시:
Score Summary: Fluency 3 / Accuracy 2 / Vocabulary 3 / Pronunciation 2 / Coherence 3
Strengths: 예) 자연스러운 속도로 말함, 기본 어휘 적절
Areas to Improve: 예) 과거형 오류 반복, 문장 연결 부족
Next Step: 예) "Try describing a past event using 'first-then-finally' structure."""""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
    
    def _setup_graph(self):
        """Configure LangGraph workflow."""
        # Create StateGraph
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("assess_pronunciation", self._assess_pronunciation_node)
        workflow.add_node("evaluate", self._evaluate_node)
        
        # Configure edges
        workflow.set_entry_point("generate_response")
        workflow.add_edge("generate_response", "assess_pronunciation")
        workflow.add_edge("assess_pronunciation", "evaluate")
        workflow.add_edge("evaluate", END)
        
        # Compile graph (with memory checkpointer)
        self.graph = workflow.compile(checkpointer=self.memory)
    
    def _generate_response_node(self, state: ConversationState) -> ConversationState:
        """Node for generating conversation response."""
        user_input = state["user_input"]
        messages = state.get("messages", [])
        
        # Convert message history to LangChain message objects
        chat_history = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                chat_history.append(HumanMessage(content=content))
            elif role == "assistant":
                chat_history.append(AIMessage(content=content))
        
        # Create prompt and invoke LLM
        chain = self.conversation_prompt | self.llm
        response = chain.invoke({
            "input": user_input,
            "chat_history": chat_history
        })
        
        # Update state
        state["assistant_response"] = response.content
        state["messages"].append({"role": "user", "content": user_input})
        state["messages"].append({"role": "assistant", "content": response.content})
        
        return state
    
    def _assess_pronunciation_node(self, state: ConversationState) -> ConversationState:
        """Node for pronunciation assessment using Azure Speech Service."""
        
        audio_data = state.get("audio_data")
        user_input = state.get("user_input", "")
        
        # Perform assessment if audio data is present
        if audio_data:
            try:
                # Run async function synchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                pronunciation_result = loop.run_until_complete(
                    self.audio_service.assess_pronunciation(audio_data, user_input)
                )
                loop.close()
                
                if pronunciation_result:
                    state["pronunciation_result"] = pronunciation_result
                    logger.info(f"Assessment Node: Success - Score: {pronunciation_result.get('pronunciation_score', 0)}")
                else:
                    state["pronunciation_result"] = None
                    logger.warning("Assessment Node: Assessment failed")
            except Exception as e:
                logger.error(f"Assessment Node Error: {str(e)}", exc_info=True)
                state["pronunciation_result"] = None
        else:
            state["pronunciation_result"] = None
            logger.info("Assessment Node: No audio data")
        
        return state
    
    def _evaluate_node(self, state: ConversationState) -> ConversationState:
        """Node for evaluation (Text + Pronunciation)."""
        messages = state.get("messages", [])
        pronunciation_result = state.get("pronunciation_result")

        
        # Convert conversation to text
        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"
        
        # Create and invoke evaluation chain
        chain = self.evaluation_prompt | self.llm
        response = chain.invoke({"conversation_text": conversation_text})
        
        # Parse JSON
        content = response.content
        try:
            if isinstance(content, str):
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    evaluation_data = json.loads(json_str)
                else:
                    evaluation_data = {
                        "grammar_score": 75,
                        "vocabulary_score": 75,
                        "fluency_score": 75,
                        "communication_score": 75,
                        "overall_score": 75,
                        "feedback": content,
                        "suggestions": [],
                        "strengths": [],
                        "weaknesses": []
                    }
            else:
                evaluation_data = content
            
            # Integrate assessment results
            if pronunciation_result:
                # Apply Azure pronunciation scores
                pronunciation_score = pronunciation_result.get("pronunciation_score", 0)
                accuracy_score = pronunciation_result.get("accuracy_score", 0)
                fluency_score_azure = pronunciation_result.get("fluency_score", 0)
                prosody_score = pronunciation_result.get("prosody_score", 0)
                
                # Weighted average for fluency
                original_fluency = evaluation_data.get("fluency_score", 75)
                combined_fluency = (original_fluency * 0.4 + fluency_score_azure * 0.6)
                
                evaluation_data["fluency_score"] = round(combined_fluency, 1)
                evaluation_data["pronunciation_score"] = pronunciation_score
                evaluation_data["accuracy_score"] = accuracy_score
                evaluation_data["prosody_score"] = prosody_score
                
                # Add detailed pronunciation info
                evaluation_data["pronunciation_details"] = {
                    "pronunciation_score": pronunciation_score,
                    "accuracy_score": accuracy_score,
                    "fluency_score": fluency_score_azure,
                    "completeness_score": pronunciation_result.get("completeness_score", 0),
                    "prosody_score": prosody_score,
                    "recognized_text": pronunciation_result.get("recognized_text", ""),
                    "word_details": pronunciation_result.get("word_details", [])
                }
                
                # Recalculate overall score with pronunciation
                overall_score = (
                    evaluation_data.get("grammar_score", 0) * 0.2 +
                    evaluation_data.get("vocabulary_score", 0) * 0.2 +
                    combined_fluency * 0.2 +
                    pronunciation_score * 0.2 +
                    evaluation_data.get("comprehension_score", evaluation_data.get("communication_score", 0)) * 0.2
                )
                evaluation_data["overall_score"] = round(overall_score, 1)
            
            # Normalize score
            overall_score = evaluation_data.get("overall_score", 0)
            overall_score = max(0, min(100, overall_score))
            
            state["evaluation_result"] = {
                "score": float(overall_score),
                "feedback": evaluation_data.get("feedback", ""),
                "suggestions": evaluation_data.get("suggestions", []),
                "evaluation_details": {
                    "grammar_score": evaluation_data.get("grammar_score", 0),
                    "vocabulary_score": evaluation_data.get("vocabulary_score", 0),
                    "fluency_score": evaluation_data.get("fluency_score", 0),
                    "communication_score": evaluation_data.get("communication_score", 0),
                    "comprehension_score": evaluation_data.get("comprehension_score", evaluation_data.get("communication_score", 0)),
                    "pronunciation_score": evaluation_data.get("pronunciation_score", 0),
                    "accuracy_score": evaluation_data.get("accuracy_score", 0),
                    "prosody_score": evaluation_data.get("prosody_score", 0),
                    "strengths": evaluation_data.get("strengths", []),
                    "weaknesses": evaluation_data.get("weaknesses", []),
                    "error_types": evaluation_data.get("error_types", {}),
                    "corrections": evaluation_data.get("corrections", []),
                    "category_feedback": evaluation_data.get("category_feedback", {}),
                    "pronunciation_details": evaluation_data.get("pronunciation_details", {})
                }
            }
        except Exception as e:
            state["evaluation_result"] = {
                "score": 0.0,
                "feedback": f"평가 중 오류가 발생했습니다: {str(e)}",
                "suggestions": ["다시 시도해주세요."],
                "evaluation_details": {}
            }
        
        return state
    
    async def evaluate_conversation(
        self, 
        text: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Evaluate conversation content.

        Args:
            text: The text to evaluate.
            conversation_history: The history of the conversation.

        Returns:
            Dict[str, Any]: The evaluation results.
        """
        # Combine history and current text
        conversation_text = ""
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                conversation_text += f"{role}: {content}\n"
        # Add text if present
        if text:
            conversation_text += f"user: {text}\n"
        
        # Create evaluation chain
        evaluation_chain = self.evaluation_prompt | self.llm
        
        try:
            response = await evaluation_chain.ainvoke({
                "conversation_text": conversation_text
            })
            
            # Try parsing JSON
            content = response.content
            if isinstance(content, str):
                # Extract JSON part
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    evaluation_data = json.loads(json_str)
                else:
                    # Return default if not JSON
                    evaluation_data = {
                        "grammar_score": 75,
                        "vocabulary_score": 75,
                        "fluency_score": 75,
                        "communication_score": 75,
                        "overall_score": 75,
                        "feedback": content,
                        "suggestions": [],
                        "strengths": [],
                        "weaknesses": []
                    }
            else:
                evaluation_data = content
            
            # Normalize score
            overall_score = evaluation_data.get("overall_score", 0)
            if overall_score > 100:
                overall_score = 100
            elif overall_score < 0:
                overall_score = 0
            
            return {
                "score": float(overall_score),
                "feedback": evaluation_data.get("feedback", ""),
                "suggestions": evaluation_data.get("suggestions", []),
                "evaluation_details": {
                    "grammar_score": evaluation_data.get("grammar_score", 0),
                    "vocabulary_score": evaluation_data.get("vocabulary_score", 0),
                    "fluency_score": evaluation_data.get("fluency_score", 0),
                    "communication_score": evaluation_data.get("communication_score", 0),
                    "comprehension_score": evaluation_data.get("comprehension_score", evaluation_data.get("communication_score", 0)),
                    "strengths": evaluation_data.get("strengths", []),
                    "weaknesses": evaluation_data.get("weaknesses", []),
                    "error_types": evaluation_data.get("error_types", {}),
                    "corrections": evaluation_data.get("corrections", []),
                    "category_feedback": evaluation_data.get("category_feedback", {})
                }
            }
        except Exception as e:
            # Return error response
            return {
                "score": 0.0,
                "feedback": f"평가 중 오류가 발생했습니다: {str(e)}",
                "suggestions": ["다시 시도해주세요."],
                "evaluation_details": {}
            }
    
    async def generate_response(
        self, 
        user_input: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """Generate conversation response.

        Args:
            user_input: The user's input text.
            conversation_history: The conversation history.

        Returns:
            str: The generated response.
        """
        # Convert message history to LangChain message objects
        chat_history = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    chat_history.append(HumanMessage(content=content))
                elif role == "assistant":
                    chat_history.append(AIMessage(content=content))
        
        # Create conversation chain

        conversation_chain = self.conversation_prompt | self.llm
        
        try:
            response = await conversation_chain.ainvoke({
                "input": user_input,
                "chat_history": chat_history
            })
            
            return response.content
        except Exception as e:
            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"

