"""
Pydantic schemas for Document upload, listing, metadata, and Admin statistics.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Document metadata returned to authenticated users and administrators."""

    id: int
    filename: str
    file_type: str
    file_size: int = 0
    page_count: Optional[int] = 1
    chunk_count: int = 0
    summary: Optional[str] = None
    error_message: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploader_name: Optional[str] = None
    upload_timestamp: datetime
    processing_status: str

    class Config:
        orm_mode = True
        from_attributes = True


class DocumentChunkPreview(BaseModel):
    """Preview of an individual chunk belonging to a document."""

    id: int
    document_id: int
    chunk_index: int
    page_number: Optional[int] = None
    chunk_text: str
    metadata: Optional[Dict[str, Any]] = None


class DocumentDetailResponse(DocumentResponse):
    """Detailed document response including chunk previews."""

    chunks: List[DocumentChunkPreview] = []


class AdminStatsResponse(BaseModel):
    """Summary metrics displayed on the PolicyDesk Admin Dashboard."""

    total_documents: int
    processed_documents: int
    failed_documents: int
    processing_documents: int
    total_chunks: int
    total_users: int
    total_conversations: int
    recent_uploads: List[DocumentResponse]
