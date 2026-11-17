from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    """Input message schema conforming to AI SDK and FastAPI chat contracts."""

    role: Literal["user", "assistant", "system"]
    content: str


class ChatStreamRequest(BaseModel):
    """Request payload sent by the frontend for streaming chat completions."""

    threadId: uuid.UUID
    messages: list[ChatMessageIn]
