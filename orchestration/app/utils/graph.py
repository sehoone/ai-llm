"""This file contains the graph utilities for the application."""

from typing import List, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.messages import trim_messages as _trim_messages

from app.core.config import settings
from app.core.logging import logger
from app.schemas import Message


def dump_messages(messages: Union[list[Message], list[dict]]) -> list[dict]:
    """Dump the messages to a list of dictionaries.

    Handles file attachments by converting them to OpenAI vision format.

    Args:
        messages: The messages to dump. Can be list of Message objects or dicts.

    Returns:
        list[dict]: The dumped messages.
    """
    result = []
    for message in messages:
        # Handle dict messages (already dumped)
        if isinstance(message, dict):
            result.append(message)
            continue
        
        # Handle LangChain BaseMessage objects (HumanMessage, AIMessage, etc.)
        if isinstance(message, BaseMessage):
            # LangChain messages use 'type' attribute for role
            role_map = {
                "human": "user",
                "ai": "assistant", 
                "system": "system",
                "tool": "tool",
            }
            msg_type = getattr(message, 'type', None)
            role = role_map.get(msg_type, msg_type)
            result.append({"role": role, "content": message.content})
            continue
        
        # Handle Message schema objects
        if not hasattr(message, 'role') or not hasattr(message, 'content'):
            # Skip invalid message formats
            logger.warning("invalid_message_format", message_type=type(message).__name__)
            continue
            
        msg_dict = {"role": message.role}
        
        # Check if message has file attachments
        if hasattr(message, 'files') and message.files and message.role == "user":
            # Build content array for multimodal message
            content_parts = []
            
            # Add text content
            content_parts.append({
                "type": "text",
                "text": message.content
            })
            
            # Add file attachments
            for file in message.files:
                if file.is_image():
                    # Add image as vision content
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{file.content_type};base64,{file.data}",
                            "detail": "auto"
                        }
                    })
                elif file.is_text():
                    # Add text file content as additional text
                    try:
                        file_content = file.get_text_content()
                        content_parts.append({
                            "type": "text",
                            "text": f"\n\n--- Content from {file.filename} ---\n{file_content}\n--- End of {file.filename} ---"
                        })
                    except Exception as e:
                        logger.warning("failed_to_read_text_file", filename=file.filename, error=str(e))
                elif file.is_pdf():
                    # For PDF, we'd need a PDF parser - for now add a placeholder
                    content_parts.append({
                        "type": "text",
                        "text": f"\n\n[PDF file attached: {file.filename}. PDF content extraction not yet implemented.]"
                    })
            
            msg_dict["content"] = content_parts
        else:
            msg_dict["content"] = message.content
        
        result.append(msg_dict)
    
    return result


def process_llm_response(response: BaseMessage) -> BaseMessage:
    """Process LLM response to handle structured content blocks (e.g., from GPT-5 models).

    GPT-5 models return content as a list of blocks like:
    [
        {'id': '...', 'summary': [], 'type': 'reasoning'},
        {'type': 'text', 'text': 'actual response'}
    ]

    This function extracts the actual text content from such structures.

    Args:
        response: The raw response from the LLM

    Returns:
        BaseMessage with processed content
    """
    if isinstance(response.content, list):
        # Extract text from content blocks
        text_parts = []
        for block in response.content:
            if isinstance(block, dict):
                # Handle text blocks
                if block.get("type") == "text" and "text" in block:
                    text_parts.append(block["text"])
                # Log reasoning blocks for debugging
                elif block.get("type") == "reasoning":
                    logger.debug(
                        "reasoning_block_received",
                        reasoning_id=block.get("id"),
                        has_summary=bool(block.get("summary")),
                    )
            elif isinstance(block, str):
                text_parts.append(block)

        # Join all text parts
        response.content = "".join(text_parts)
        logger.debug(
            "processed_structured_content",
            block_count=len(response.content) if isinstance(response.content, list) else 1,
            extracted_length=len(response.content) if isinstance(response.content, str) else 0,
        )

    return response


def prepare_messages(messages: list[Message], llm: BaseChatModel, system_prompt: str) -> list[dict]:
    """Prepare the messages for the LLM.

    Args:
        messages (list[Message]): The messages to prepare.
        llm (BaseChatModel): The LLM to use.
        system_prompt (str): The system prompt to use.

    Returns:
        list[dict]: The prepared messages as dictionaries ready for LLM.
    """
    dumped = dump_messages(messages)
    logger.debug("prepare_messages_dumped", message_count=len(dumped), messages=dumped)
    
    try:
        trimmed_messages = _trim_messages(
            dumped,
            strategy="last",
            token_counter=llm,
            max_tokens=settings.MAX_TOKENS,
            start_on="human",
            include_system=False,
            allow_partial=False,
        )
        logger.debug("prepare_messages_trimmed", trimmed_count=len(trimmed_messages))
    except ValueError as e:
        # Handle unrecognized content blocks (e.g., reasoning blocks from GPT-5)
        if "Unrecognized content block type" in str(e):
            logger.warning(
                "token_counting_failed_skipping_trim",
                error=str(e),
                message_count=len(messages),
            )
            # Skip trimming and return all messages as dicts
            trimmed_messages = dumped
        else:
            raise

    result = [{"role": "system", "content": system_prompt}] + trimmed_messages
    logger.debug("prepare_messages_result", total_count=len(result))
    return result
