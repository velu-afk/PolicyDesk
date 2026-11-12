"""
Conversational RAG Chat API routes:
- POST /api/chat/ask
- GET /api/chat/conversations
- GET /api/chat/conversations/{conversation_id}
- DELETE /api/chat/conversations/{conversation_id}
- PATCH /api/chat/messages/{message_id}/feedback

Strictly enforces per-user conversation ownership (users can never view or delete
conversations belonging to another user).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import Session, get_db
from app.dependencies.auth import get_current_user
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.chat import (
    AskQuestionRequest,
    AskQuestionResponse,
    ConversationDetailResponse,
    ConversationSummaryResponse,
    MessageFeedbackRequest,
    MessageResponse,
)
from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/chat", tags=["RAG Chat"])


@router.post(
    "/ask",
    response_model=AskQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question grounded strictly in uploaded policy documents",
)
def ask_question(
    payload: AskQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AskQuestionResponse:
    """
    Submit a question to the PolicyDesk RAG pipeline.
    Generates query embeddings, retrieves matching chunks above similarity threshold,
    and synthesizes a source-grounded answer with exact passages and page numbers.
    """
    return rag_service.answer_question(db=db, user=current_user, payload=payload)


@router.get(
    "/conversations",
    response_model=List[ConversationSummaryResponse],
    summary="List the current user's conversation history",
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ConversationSummaryResponse]:
    """Return all conversations owned by the currently authenticated user."""
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    summaries: List[ConversationSummaryResponse] = []
    for c in convs:
        msg_count = (
            db.query(Message).filter(Message.conversation_id == c.id).count()
        )
        summaries.append(
            ConversationSummaryResponse(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                message_count=msg_count,
                created_at=c.created_at,
            )
        )
    return summaries


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get full message transcript and citations for a conversation",
)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetailResponse:
    """
    Retrieve a specific conversation and its chronological messages.
    Enforces strict user ownership (returns HTTP 403 if owned by another user).
    """
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    if conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you cannot view conversations belonging to another user.",
        )

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ConversationDetailResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        messages=[MessageResponse.from_orm(m) for m in messages],
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a conversation and all its messages",
)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete a conversation owned by the current user.
    Returns HTTP 403 if the conversation belongs to a different user.
    """
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    if conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you cannot delete conversations belonging to another user.",
        )

    msgs = db.query(Message).filter(Message.conversation_id == conv.id).all()
    for m in msgs:
        db.delete(m)
    db.delete(conv)
    db.commit()
    return {
        "message": "Conversation deleted successfully.",
        "deleted_conversation_id": conversation_id,
    }


@router.patch(
    "/messages/{message_id}/feedback",
    response_model=MessageResponse,
    summary="Submit helpful / not_helpful feedback on an AI response",
)
def submit_message_feedback(
    message_id: int,
    payload: MessageFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Record user quality feedback ('helpful' or 'not_helpful') on an assistant message."""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found.",
        )
    conv = db.query(Conversation).filter(Conversation.id == msg.conversation_id).first()
    if conv is None or conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you cannot rate messages in another user's conversation.",
        )

    msg.feedback = payload.feedback
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return MessageResponse.from_orm(msg)
