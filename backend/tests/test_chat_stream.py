from __future__ import annotations

import json
import uuid

import httpx
import pytest
from starlette.testclient import TestClient

from app.assistant.agent import create_document_agent
from app.auth.dependencies import CurrentUser, get_current_user
from app.chat.messages import ChatMessageIn
from app.chat.orchestrator import stream_chat_turn
from app.chat.streaming import format_sse
from app.database.chats import create_user_thread, get_user_thread, list_thread_messages
from app.database.session import SessionLocal
from app.main import app


def test_format_sse() -> None:
    event_str = format_sse({"delta": "Apple net sales"}, event="text")
    assert event_str == 'event: text\ndata: {"delta": "Apple net sales"}\n\n'

    data_only = format_sse({"status": "ok"})
    assert data_only == 'data: {"status": "ok"}\n\n'


def test_document_agent_tools_registered() -> None:
    agent = create_document_agent()
    # PydanticAI Agent maintains a function toolset
    tools = getattr(agent, "_function_toolset", None)
    tool_names = list(tools.tools.keys()) if tools else list(getattr(agent, "_function_tools", {}).keys())
    assert "search_filings" in tool_names
    assert "read_chunk" in tool_names
    assert "read_surrounding_chunks" in tool_names


@pytest.mark.anyio
async def test_stream_chat_turn_unauthorized_thread() -> None:
    dummy_user = CurrentUser(id="user-123", email="analyst@driftwood.com")
    random_thread_id = uuid.uuid4()

    with SessionLocal() as db:
        events = []
        async for chunk in stream_chat_turn(
            thread_id=random_thread_id,
            messages=[ChatMessageIn(role="user", content="Hello")],
            user=dummy_user,
            db=db,
        ):
            events.append(chunk)

        assert len(events) == 1
        assert "event: error" in events[0]
        assert "not found" in events[0]


@pytest.mark.integration
@pytest.mark.anyio
async def test_stream_chat_turn_end_to_end() -> None:
    test_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
    dummy_user = CurrentUser(id=test_user_id, email="analyst@driftwood.com")

    with SessionLocal() as db:
        # Create thread
        thread = create_user_thread(db, user_id=test_user_id, title="New Research Chat")
        thread_id = thread.id

        events = []
        async for chunk in stream_chat_turn(
            thread_id=thread_id,
            messages=[
                ChatMessageIn(
                    role="user",
                    content="What does the latest 10-K say about Apple's iPhone revenue?",
                )
            ],
            user=dummy_user,
            db=db,
        ):
            events.append(chunk)

        # Verify stream contains text and citations
        full_stream = "".join(events)
        assert "event: text" in full_stream
        assert "event: citations" in full_stream
        assert "event: done" in full_stream

        # Verify database persistence
        messages = list_thread_messages(db, thread_id=thread_id, user_id=test_user_id)
        assert messages is not None
        assert len(messages) >= 2  # 1 user + 1 assistant

        user_m = messages[0]
        assert user_m.role == "user"
        assert "iPhone" in user_m.content

        assistant_m = messages[1]
        assert assistant_m.role == "assistant"
        assert len(assistant_m.content) > 0


@pytest.mark.anyio
async def test_chat_stream_api_endpoint() -> None:
    test_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
    mock_user = CurrentUser(id=test_user_id, email="analyst@driftwood.com")

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        with SessionLocal() as db:
            thread = create_user_thread(db, user_id=test_user_id, title="Test API Stream")
            thread_id = thread.id

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/chat/stream",
                json={
                    "threadId": str(thread_id),
                    "messages": [
                        {"role": "user", "content": "Summarize Microsoft cloud revenue growth."}
                    ],
                },
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "event: text" in body
        assert "event: done" in body
    finally:
        app.dependency_overrides.clear()
