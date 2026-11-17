from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import structlog
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.google import GoogleProvider

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.config import settings

logger = structlog.get_logger(__name__)

INSTRUCTIONS_PATH = Path(__file__).resolve().parent / "instructions.md"
SYSTEM_INSTRUCTIONS = (
    INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    if INSTRUCTIONS_PATH.exists()
    else "You are Document Copilot. Ground all answers in retrieved SEC filings."
)


def _resolve_model(model: Any | None = None) -> Any:
    """Resolve the LLM model to use, falling back to TestModel when no Gemini API key is set."""
    if model is not None:
        return model

    api_key = settings.effective_gemini_api_key
    if api_key and not api_key.startswith("your-") and api_key != "mock":
        os.environ.setdefault("GEMINI_API_KEY", api_key)
        os.environ.setdefault("GOOGLE_API_KEY", api_key)
        return GoogleModel(
            settings.llm_model,
            provider=GoogleProvider(api_key=api_key),
        )

    logger.warning("GEMINI_API_KEY is not configured; using TestModel for agent.")
    return TestModel()


def create_document_agent(
    model: Any | None = None,
) -> Agent[DocumentAgentDeps, GroundedAnswer]:
    """Create and configure the PydanticAI Document Copilot Agent with tools."""
    resolved_model = _resolve_model(model)

    agent: Agent[DocumentAgentDeps, GroundedAnswer] = Agent(
        model=resolved_model,
        output_type=GroundedAnswer,
        instructions=SYSTEM_INSTRUCTIONS,
        deps_type=DocumentAgentDeps,
    )

    @agent.tool
    def search_filings(
        ctx: RunContext[DocumentAgentDeps],
        query: str,
        ticker: str | None = None,
    ) -> str:
        """Search SEC filings using hybrid semantic vector and full-text keyword retrieval."""
        passages = ctx.deps.retriever.search(query, ticker=ticker, limit=5)
        ctx.deps.retrieved_passages.extend(passages)
        if not passages:
            return f"No filings matched query '{query}'" + (f" for ticker {ticker}" if ticker else "")

        summary_lines = []
        for p in passages:
            summary_lines.append(
                f"[Chunk {p.chunk_id}] {p.ticker} ({p.form}, filing date {p.filing_date}, Item: {p.section or 'General'}):\n"
                f"{p.content}\n"
            )
        return "\n---\n".join(summary_lines)

    @agent.tool
    def read_chunk(
        ctx: RunContext[DocumentAgentDeps],
        chunk_id: str,
    ) -> str:
        """Read the full content and metadata of a specific chunk by its chunk_id UUID."""
        try:
            cid = uuid.UUID(chunk_id)
        except ValueError:
            return f"Invalid chunk_id UUID format: '{chunk_id}'"

        passage = ctx.deps.retriever.get_chunk_by_id(cid)
        if not passage:
            return f"Chunk {chunk_id} not found."

        ctx.deps.retrieved_passages.append(passage)
        return (
            f"[Chunk {passage.chunk_id}] {passage.ticker} {passage.form} (filed {passage.filing_date}):\n"
            f"{passage.content}"
        )

    @agent.tool
    def read_surrounding_chunks(
        ctx: RunContext[DocumentAgentDeps],
        chunk_id: str,
        window: int = 1,
    ) -> str:
        """Retrieve adjacent context chunks before and after the target chunk to examine surrounding text or tables."""
        try:
            cid = uuid.UUID(chunk_id)
        except ValueError:
            return f"Invalid chunk_id UUID format: '{chunk_id}'"

        surrounding = ctx.deps.retriever.get_surrounding_chunks(cid, window=window)
        if not surrounding:
            return f"No surrounding chunks found for {chunk_id}."

        ctx.deps.retrieved_passages.extend(surrounding)
        output = [f"Surrounding context for chunk {chunk_id}:"]
        for p in surrounding:
            output.append(
                f"\n[Chunk {p.chunk_id} | Index {p.chunk_index}]:\n{p.content}"
            )
        return "\n".join(output)

    return agent


document_agent = create_document_agent()
