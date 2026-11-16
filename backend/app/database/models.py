import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str]
    form: Mapped[str]
    filing_date: Mapped[date]
    accession_number: Mapped[str] = mapped_column(unique=True)
    source_url: Mapped[str]
    markdown: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1536))
    search_vector = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document: Mapped[SourceDocument] = relationship(back_populates="chunks")


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(default="New Chat")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    thread: Mapped[ChatThread] = relationship(back_populates="messages")
    citations: Mapped[list["MessageCitation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class MessageCitation(Base):
    __tablename__ = "message_citations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True
    )
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    message: Mapped[ChatMessage] = relationship(back_populates="citations")
    chunk: Mapped[DocumentChunk] = relationship()
