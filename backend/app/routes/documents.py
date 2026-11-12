"""
Document listing routes accessible to authenticated users:
- GET /api/documents
- GET /api/documents/{document_id}
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import Session, get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.document import DocumentDetailResponse, DocumentResponse
from app.services.document_service import document_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get(
    "",
    response_model=List[DocumentResponse],
    summary="List processed documents available in the knowledge base",
)
def list_available_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DocumentResponse]:
    """Return all successfully processed documents available for Q&A."""
    return document_service.list_documents(db=db, processed_only=True)


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="View details and passages of a processed document",
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    """Return document metadata and chunks for a processed document."""
    detail = document_service.get_document_detail(db=db, document_id=document_id)
    if detail.processing_status != "processed" and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or not yet processed.",
        )
    return detail
