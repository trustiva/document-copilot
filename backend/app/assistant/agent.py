from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import structlog
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel

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
    """Resolve the LLM model to use, falling back to TestModel when no API key is set."""
    if model is not None:
        return model

    api_key = settings.openai_api_key
    if api_key and not api_key.startswith("your-") and api_key != "mock":
        os.environ.setdefault("OPENAI_API_KEY", api_key)
        return OpenAIChatModel(settings.llm_model)

    logger.warning("OPENAI_API_KEY is not configured; using TestModel for agent.")
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
        passages = ctx.deps.retriever.search(query, ticker=ticker, limit=8)
        ctx.deps.retrieved_passages.extend(passages)
        if not passages:
            return "No matching SEC filing passages found for query."

        formatted: list[str] = []
        for p in passages:
            formatted.append(
                f"--- CHUNK ID: {p.chunk_id} | {p.ticker} {p.form} {p.filing_date} (Score: {p.score:.3f}) ---\n"
                f"{p.content}\n"
            )
        return "\n".join(formatted)

    @agent.tool
    def read_chunk(ctx: RunContext[DocumentAgentDeps], chunk_id: str) -> str:
        """Fetch the full content of a specific chunk by its UUID string."""
        try:
            cid = uuid.UUID(chunk_id.strip())
        except ValueError:
            return f"Invalid UUID format: {chunk_id}"

        passage = ctx.deps.retriever.get_chunk_by_id(cid)
        if not passage:
            return f"Chunk {chunk_id} not found."

        ctx.deps.retrieved_passages.append(passage)
        return (
            f"--- CHUNK ID: {passage.chunk_id} | {passage.ticker} {passage.form} {passage.filing_date} ---\n"
            f"{passage.content}"
        )

    @agent.tool
    def read_surrounding_chunks(
        ctx: RunContext[DocumentAgentDeps],
        chunk_id: str,
        window: int = 1,
    ) -> str:
        """Fetch surrounding chunks (+/- window) around a chunk ID for broader context."""
        try:
            cid = uuid.UUID(chunk_id.strip())
        except ValueError:
            return f"Invalid UUID format: {chunk_id}"

        surrounding = ctx.deps.retriever.get_surrounding_chunks(cid, window=window)
        if not surrounding:
            return f"No surrounding chunks found for {chunk_id}."

        ctx.deps.retrieved_passages.extend(surrounding)
        formatted: list[str] = []
        for p in surrounding:
            formatted.append(
                f"--- CHUNK #{p.chunk_index} | ID: {p.chunk_id} | {p.ticker} {p.form} {p.filing_date} ---\n"
                f"{p.content}\n"
            )
        return "\n".join(formatted)

    return agent


# Global default agent instance
document_agent = create_document_agent()
