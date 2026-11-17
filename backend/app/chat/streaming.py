from __future__ import annotations

import json
from typing import Any


def format_sse(data: Any, event: str | None = None) -> str:
    """Format data into standard Server-Sent Events (SSE) string."""
    payload = json.dumps(data, default=str) if not isinstance(data, str) else data
    if event:
        return f"event: {event}\ndata: {payload}\n\n"
    return f"data: {payload}\n\n"
