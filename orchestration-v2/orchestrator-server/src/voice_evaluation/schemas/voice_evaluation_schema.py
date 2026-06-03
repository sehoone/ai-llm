from typing import List, Dict, Optional, Any
from pydantic import BaseModel

class EvaluationRequest(BaseModel):
    text: str
    conversation_history: Optional[List[Dict[str, str]]] = None

class EvaluationResponse(BaseModel):
    score: float
    feedback: str
    suggestions: List[str]
    evaluation_details: Dict[str, Any]

class ConversationResponse(BaseModel):
    text: str
    audio: Optional[str] = None
    evaluation: Optional[EvaluationResponse] = None
