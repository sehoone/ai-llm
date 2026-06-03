"""This file contains the graph utilities for the application."""

from typing import Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.messages import trim_messages as _trim_messages

from src.common.config import settings
from src.common.logging import logger
from src.chatbot.schemas.chat_schema import Message


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
            role_map = {
                "human": "user",
                "ai": "assistant",
                "system": "system",
                "tool": "tool",
            }
            msg_type = getattr(message, 'type', None)
            role = role_map.get(msg_type, msg_type)
            msg_dict = {"role": role, "content": message.content}
            if msg_type == "tool" and hasattr(message, 'tool_call_id') and message.tool_call_id:
                msg_dict["tool_call_id"] = message.tool_call_id
            elif msg_type == "ai" and hasattr(message, 'tool_calls') and message.tool_calls:
                msg_dict["tool_calls"] = message.tool_calls
            result.append(msg_dict)
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


def _replace_images_with_placeholder(message: dict) -> dict:
    """Replace image content in a message with a text placeholder.

    This is used to reduce token usage by not sending the same image
    multiple times in conversation history.

    Args:
        message: A message dict that may contain multimodal content.

    Returns:
        dict: Message with images replaced by placeholders.
    """
    if not isinstance(message.get("content"), list):
        return message

    new_content = []
    image_count = 0

    for part in message["content"]:
        if isinstance(part, dict) and part.get("type") == "image_url":
            image_count += 1
        else:
            new_content.append(part)

    # Add placeholder for removed images
    if image_count > 0:
        placeholder_text = f"[이전에 첨부된 이미지 {image_count}개 - 이미 분석 완료됨]"
        new_content.append({"type": "text", "text": placeholder_text})

    return {"role": message["role"], "content": new_content if len(new_content) > 1 else new_content[0].get("text", "") if new_content else ""}


def _sanitize_tool_sequences(messages: list) -> list:
    """Remove tool_calls from assistant messages whose tool results were trimmed away.

    When trim_messages cuts history, it may keep an assistant message with tool_calls
    but drop the subsequent tool result messages. This produces a 400 from the API.
    Strip orphaned tool_calls so the sequence is always valid.

    Handles both dict messages and LangChain BaseMessage objects (trim_messages returns
    BaseMessage objects even when given dicts as input).
    """
    def _get(msg, key):
        if isinstance(msg, dict):
            return msg.get(key)
        # LangChain BaseMessage: role stored as .type ("ai"/"human"/"tool"), tool_calls as attribute
        if key == "role":
            type_map = {"ai": "assistant", "human": "user", "tool": "tool", "system": "system"}
            return type_map.get(getattr(msg, "type", None))
        if key == "tool_calls":
            return getattr(msg, "tool_calls", None) or None
        if key == "tool_call_id":
            return getattr(msg, "tool_call_id", None)
        return None

    result = list(messages)
    for i, msg in enumerate(result):
        if _get(msg, "role") == "assistant":
            tool_calls = _get(msg, "tool_calls")
            if not tool_calls:
                continue
            tool_call_ids = {tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None) for tc in tool_calls}
            following_tool_ids = {_get(m, "tool_call_id") for m in result[i + 1:] if _get(m, "role") == "tool"}
            if not tool_call_ids.issubset(following_tool_ids):
                if isinstance(msg, dict):
                    result[i] = {k: v for k, v in msg.items() if k != "tool_calls"}
                else:
                    # LangChain AIMessage: clear tool_calls in-place via copy
                    from langchain_core.messages import AIMessage
                    result[i] = AIMessage(content=msg.content)
    return result


def prepare_messages(messages: list[Message], llm: BaseChatModel, system_prompt: str) -> list[dict]:
    """Prepare the messages for the LLM.

    Images are only kept in the last user message to reduce token usage.
    Previous images are replaced with placeholders.

    Args:
        messages (list[Message]): The messages to prepare.
        llm (BaseChatModel): The LLM to use.
        system_prompt (str): The system prompt to use.

    Returns:
        list[dict]: The prepared messages as dictionaries ready for LLM.
    """
    dumped = dump_messages(messages)

    # Replace images in all messages except the last user message
    # Find the last user message index
    last_user_idx = -1
    for i in range(len(dumped) - 1, -1, -1):
        if dumped[i].get("role") == "user":
            last_user_idx = i
            break

    # Process messages: replace images with placeholders except for the last user message
    processed_messages = []
    for i, msg in enumerate(dumped):
        if i == last_user_idx:
            # Keep the last user message as-is (with images)
            processed_messages.append(msg)
        elif msg.get("role") == "user" and isinstance(msg.get("content"), list):
            # Replace images in previous user messages
            processed_messages.append(_replace_images_with_placeholder(msg))
        else:
            processed_messages.append(msg)

    try:
        trimmed_messages = _trim_messages(
            processed_messages,
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
            trimmed_messages = processed_messages
        else:
            raise

    sanitized_messages = _sanitize_tool_sequences(trimmed_messages)
    result = [{"role": "system", "content": system_prompt}] + sanitized_messages
    logger.debug("prepare_messages_result", total_count=len(result))
    return result
