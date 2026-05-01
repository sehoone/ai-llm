"""This file contains the graph schema for the application."""

from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
)


class GraphState(BaseModel):
    """State definition for the LangGraph Agent/Workflow."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )
    model_name: str | None = Field(default=None, description="Logical model name passed to LLMService.call()")
    long_term_memory: str = Field(default="", description="The long term memory of the conversation")
    is_deep_thinking: bool = Field(default=False, description="Whether deep thinking mode is enabled")
    system_instructions: str | None = Field(default=None, description="Custom instructions for the GPT")
    rag_key: str | None = Field(default=None, description="RAG key for the GPT knowledge base")
    thinking_context: str | None = Field(default=None, description="Execution plan from think node injected into chat")
