from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.orm import Session

from app.assistant.agent import document_agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import Citation, GroundedAnswer
from app.auth.dependencies import CurrentUser
from app.chat.messages import ChatMessageIn
from app.chat.streaming import format_sse
from app.database.chats import (
    create_assistant_message_with_citations,
    create_thread_message,
    get_user_thread,
)
from app.grounding.validator import GroundingValidator
from app.retrieval.retriever import DocumentRetriever

logger = structlog.get_logger(__name__)


async def stream_chat_turn(
    thread_id: uuid.UUID,
    messages: list[ChatMessageIn],
    user: CurrentUser,
    db: Session,
) -> AsyncGenerator[str, None]:
    """Orchestrate a complete chat turn end-to-end:

    1. Validate thread ownership
    2. Persist user message & update title
    3. Run PydanticAI agent with hybrid retriever tools
    4. Enforce grounding and citation validation
    5. Stream tokens and citation metadata via SSE
    6. Persist assistant message and citations to database
    """
    thread = get_user_thread(db, thread_id=thread_id, user_id=user.id)
    if not thread:
        yield format_sse({"error": f"Thread {thread_id} not found or unauthorized"}, event="error")
        return

    # Find the latest user message
    user_msg = next((m for m in reversed(messages) if m.role == "user"), None)
    if not user_msg or not user_msg.content.strip():
        yield format_sse({"error": "No user message content provided"}, event="error")
        return

    try:
        # Persist the incoming user message
        create_thread_message(db, thread, role="user", content=user_msg.content)

        # Auto-update thread title on first turn
        if thread.title in ("New Chat", "New Research Chat"):
            clean_title = user_msg.content.strip().split("\n")[0][:45]
            thread.title = clean_title if clean_title else "Research Thread"
            db.commit()

        # Initialize runtime dependencies
        deps = DocumentAgentDeps(
            user_id=user.id,
            thread_id=thread_id,
            retriever=DocumentRetriever(session=db),
            grounding_validator=GroundingValidator(),
        )

        logger.info(
            "Invoking Document Copilot Agent",
            thread_id=str(thread_id),
            user_id=user.id,
            prompt=user_msg.content[:80],
        )

        # Run PydanticAI agent with graceful fallback if OpenAI quota / model execution fails
        try:
            result = await document_agent.run(user_msg.content, deps=deps)
            raw_answer: GroundedAnswer = getattr(result, "output", getattr(result, "data", None))
        except Exception as exc:
            logger.warning(
                "Document agent run failed; generating grounded synthesis directly from retrieved passages.",
                error=str(exc),
            )
            passages = deps.retriever.search(user_msg.content, limit=5)
            deps.retrieved_passages.extend(passages)
            if passages:
                top_p = passages[0]
                raw_answer = GroundedAnswer(
                    answer=(
                        f"Based on the retrieved SEC filing disclosures for {top_p.ticker} ({top_p.form}, filing date {top_p.filing_date}):\n\n"
                        f"{top_p.content}\n\n"
                        f"*(Grounded directly from SEC EDGAR accession {top_p.accession_number})*"
                    ),
                    citations=[Citation(chunk_id=top_p.chunk_id, quote=top_p.content[:60].strip())],
                    has_sufficient_evidence=True,
                )
            else:
                raw_answer = GroundedAnswer(
                    answer="The available SEC filings do not contain sufficient evidence to answer this question.",
                    citations=[],
                    has_sufficient_evidence=False,
                )

        # Enforce grounding trust contract
        validated_answer: GroundedAnswer = deps.grounding_validator.enforce_or_fallback(
            raw_answer,
            deps.retrieved_passages,
        )

        # Stream answer text tokens incrementally for real-time analyst feedback
        words = validated_answer.answer.split(" ")
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            yield format_sse({"delta": token}, event="text")
            await asyncio.sleep(0.015)

        # Format and stream citations and verified source passages
        citations_data = [
            {"chunk_id": c.chunk_id, "quote": c.quote, "explanation": c.explanation}
            for c in validated_answer.citations
        ]
        passages_data = [p.model_dump(mode="json") for p in validated_answer.cited_passages]

        yield format_sse(
            {
                "citations": [
                    {"chunk_id": str(c["chunk_id"]), "quote": c["quote"]}
                    for c in citations_data
                ],
                "cited_passages": passages_data,
                "has_sufficient_evidence": validated_answer.has_sufficient_evidence,
            },
            event="citations",
        )

        # Persist assistant message and citations atomically
        assistant_msg = create_assistant_message_with_citations(
            db,
            thread=thread,
            content=validated_answer.answer,
            citations=citations_data,
        )

        # Emit completion event
        yield format_sse(
            {
                "message_id": str(assistant_msg.id),
                "thread_id": str(thread.id),
                "finishReason": "stop",
            },
            event="done",
        )

    except Exception as exc:
        logger.error(
            "Chat turn failed",
            thread_id=str(thread_id),
            user_id=user.id,
            error=str(exc),
            exc_info=True,
        )
        yield format_sse({"error": f"Internal assistant error: {exc!s}"}, event="error")
