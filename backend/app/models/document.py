"""
Document and DocumentChunk models for storing ingested documents, text chunks,
metadata, and Gemini semantic embeddings (pgvector).
"""
from datetime import datetime, timezone
from app.config import settings
from app.database import (
    Base,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    get_Vector_type,
    relationship,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, index=True)
    file_type = Column(String(32), nullable=False)  # "pdf" or "txt"
    file_size = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=True, default=1)
    chunk_count = Column(Integer, nullable=False, default=0)
    summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    uploaded_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    upload_timestamp = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    processing_status = Column(
        String(32),
        nullable=False,
        default="processing",
        index=True,
    )  # "processing", "processed", "failed"

    # Relationships
    uploader = relationship("User", back_populates="documents")
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_text = Column(Text, nullable=False)
    embedding = Column(
        get_Vector_type(settings.GEMINI_EMBEDDING_DIMENSIONS),
        nullable=False,
    )
    page_number = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_metadata = Column(JSON, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_document_chunks_doc_idx", "document_id", "chunk_index"),
    )
