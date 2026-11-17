import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.models import ChatMessage, ChatThread, MessageCitation


def list_user_threads(db: Session, user_id: str) -> list[ChatThread]:
    stmt = (
        select(ChatThread)
        .where(ChatThread.user_id == user_id)
        .order_by(ChatThread.updated_at.desc())
    )
    return list(db.scalars(stmt).all())


def create_user_thread(
    db: Session, user_id: str, title: str | None = None
) -> ChatThread:
    thread = ChatThread(
        user_id=user_id,
        title=title.strip() if title and title.strip() else "New Chat",
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def get_user_thread(
    db: Session, thread_id: uuid.UUID, user_id: str
) -> ChatThread | None:
    stmt = select(ChatThread).where(
        ChatThread.id == thread_id, ChatThread.user_id == user_id
    )
    return db.scalars(stmt).first()


def delete_user_thread(
    db: Session, thread_id: uuid.UUID, user_id: str
) -> bool:
    thread = get_user_thread(db, thread_id=thread_id, user_id=user_id)
    if not thread:
        return False
    db.delete(thread)
    db.commit()
    return True


def list_thread_messages(
    db: Session, thread_id: uuid.UUID, user_id: str
) -> list[ChatMessage] | None:
    thread = get_user_thread(db, thread_id=thread_id, user_id=user_id)
    if not thread:
        return None

    stmt = (
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .options(selectinload(ChatMessage.citations).selectinload(MessageCitation.chunk))
        .order_by(ChatMessage.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def create_thread_message(
    db: Session,
    thread: ChatThread,
    role: str,
    content: str,
) -> ChatMessage:
    message = ChatMessage(
        thread_id=thread.id,
        role=role,
        content=content,
    )
    thread.updated_at = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def create_assistant_message_with_citations(
    db: Session,
    thread: ChatThread,
    content: str,
    citations: list[dict],
) -> ChatMessage:
    """Create assistant message and persist its associated source citations atomically."""
    message = ChatMessage(
        thread_id=thread.id,
        role="assistant",
        content=content,
    )
    db.add(message)
    db.flush()

    for c in citations:
        citation_obj = MessageCitation(
            message_id=message.id,
            chunk_id=c["chunk_id"],
            quote=c.get("quote"),
        )
        db.add(citation_obj)

    thread.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message
