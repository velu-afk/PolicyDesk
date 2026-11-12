"""
Pydantic schemas for RAG Q&A, source attributions, retrieval metadata,
conversations, and answer feedback.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class SourceAttribution(BaseModel):
    """Structured citation grounded strictly in an actual retrieved DocumentChunk."""

    chunk_id: int
    source_document_id: int
    source_document_name: str
    relevant_passage: str
    page_number: Optional[int] = None
    chunk_index: int
    similarity_score: float


class RetrievalMetadata(BaseModel):
    """Diagnostic metadata about the vector retrieval and generation step."""

    query_embedding_model: str
    llm_model: str
    similarity_threshold: float
    top_k_requested: int
    chunks_evaluated: int
    chunks_above_threshold: int
    top_similarity_score: Optional[float] = None
    found_in_documents: bool


class AskQuestionRequest(BaseModel):
    """User question payload submitted to POST /api/chat/ask."""

    question: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="Question to ask against uploaded policy documents",
    )
    conversation_id: Optional[int] = Field(
        None,
        description="Optional existing conversation ID to continue a thread",
    )
    document_ids: Optional[List[int]] = Field(
        None,
        description="Optional filter restricting retrieval to specific document IDs",
    )

    @validator("question")
    def validate_question(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Question must contain at least 2 non-whitespace characters.")
        return cleaned


class AskQuestionResponse(BaseModel):
    """Structured RAG response containing answer text, grounded sources, and metadata."""

    answer: str
    conversation_id: int
    message_id: int
    sources: List[SourceAttribution]
    retrieval_metadata: RetrievalMetadata
    created_at: datetime


class MessageResponse(BaseModel):
    """Individual message in a conversation history."""

    id: int
    conversation_id: int
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    feedback: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class ConversationSummaryResponse(BaseModel):
    """Summary item for listing a user's conversations."""

    id: int
    user_id: int
    title: str
    message_count: int = 0
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """Full conversation thread with chronological messages and citations."""

    id: int
    user_id: int
    title: str
    created_at: datetime
    messages: List[MessageResponse]


class MessageFeedbackRequest(BaseModel):
    """Bonus feature: Helpful / Not Helpful feedback on AI responses."""

    feedback: str = Field(..., description="'helpful' or 'not_helpful'")

    @validator("feedback")
    def validate_feedback(cls, v: str) -> str:
        if v not in ("helpful", "not_helpful"):
            raise ValueError("Feedback must be 'helpful' or 'not_helpful'.")
        return v
