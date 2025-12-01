"""This file contains the chat schema for the application."""

import base64
import re
from typing import (
    List,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


# Supported file types for upload
SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
SUPPORTED_TEXT_TYPES = ["text/plain", "text/markdown", "text/csv", "application/json"]
SUPPORTED_DOCUMENT_TYPES = ["application/pdf"]
ALL_SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES + SUPPORTED_TEXT_TYPES + SUPPORTED_DOCUMENT_TYPES

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


class FileAttachment(BaseModel):
    """File attachment model for chat messages.

    Attributes:
        filename: Original filename
        content_type: MIME type of the file
        data: Base64 encoded file content (for API response) or raw bytes
    """

    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    data: str = Field(..., description="Base64 encoded file content")

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate that the content type is supported."""
        if v not in ALL_SUPPORTED_TYPES:
            raise ValueError(f"Unsupported file type: {v}. Supported types: {ALL_SUPPORTED_TYPES}")
        return v

    def is_image(self) -> bool:
        """Check if the file is an image."""
        return self.content_type in SUPPORTED_IMAGE_TYPES

    def is_text(self) -> bool:
        """Check if the file is a text file."""
        return self.content_type in SUPPORTED_TEXT_TYPES

    def is_pdf(self) -> bool:
        """Check if the file is a PDF."""
        return self.content_type in SUPPORTED_DOCUMENT_TYPES

    def get_text_content(self) -> str:
        """Decode and return text content for text files."""
        if not self.is_text():
            raise ValueError("Cannot get text content from non-text file")
        return base64.b64decode(self.data).decode("utf-8")


class Message(BaseModel):
    """Message model for chat endpoint.

    Attributes:
        role: The role of the message sender (user or assistant).
        content: The content of the message.
        files: Optional list of file attachments.
    """

    model_config = {"extra": "ignore"}

    role: Literal["user", "assistant", "system"] = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The content of the message", min_length=1, max_length=50000)
    files: Optional[List[FileAttachment]] = Field(default=None, description="Optional file attachments")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate the message content.

        Args:
            v: The content to validate

        Returns:
            str: The validated content

        Raises:
            ValueError: If the content contains disallowed patterns
        """
        # Check for potentially harmful content
        if re.search(r"<script.*?>.*?</script>", v, re.IGNORECASE | re.DOTALL):
            raise ValueError("Content contains potentially harmful script tags")

        # Check for null bytes
        if "\0" in v:
            raise ValueError("Content contains null bytes")

        return v


class ChatRequest(BaseModel):
    """Request model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
    """

    messages: List[Message] = Field(
        ...,
        description="List of messages in the conversation",
        min_length=1,
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint.

    Attributes:
        messages: List of messages in the conversation.
    """

    messages: List[Message] = Field(..., description="List of messages in the conversation")


class StreamResponse(BaseModel):
    """Response model for streaming chat endpoint.

    Attributes:
        content: The content of the current chunk.
        done: Whether the stream is complete.
    """

    content: str = Field(default="", description="The content of the current chunk")
    done: bool = Field(default=False, description="Whether the stream is complete")
