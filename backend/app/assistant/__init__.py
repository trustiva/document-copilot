"""Pydantic schemas for typed assistant output: GroundedAnswer, Citation, SourcePassage."""
from app.assistant.agent import create_document_agent, document_agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage

__all__ = [
    "Citation",
    "DocumentAgentDeps",
    "GroundedAnswer",
    "SourcePassage",
    "create_document_agent",
    "document_agent",
]
