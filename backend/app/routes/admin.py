"""
Administrator-only API routes:
- GET /api/admin/stats
- POST /api/admin/documents/upload
- GET /api/admin/documents
- GET /api/admin/documents/{document_id}
- DELETE /api/admin/documents/{document_id}
- GET /api/admin/users
- PATCH /api/admin/users/{user_id}

All routes strictly enforce `Depends(require_admin)` (HTTP 403 for normal users, HTTP 401 for unauthenticated).
"""
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, status

from app.database import Session, get_db
from app.dependencies.auth import require_admin
from app.models.conversation import Conversation
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.auth import UserResponse, UserRoleUpdateRequest
from app.schemas.document import (
    AdminStatsResponse,
    DocumentDetailResponse,
    DocumentResponse,
)
from app.services.auth_service import AuthService
from app.services.document_service import document_service

router = APIRouter(prefix="/api/admin", tags=["Administration"])


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get Admin Dashboard statistics and recent uploads",
)
def get_admin_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> AdminStatsResponse:
    """Return aggregated metrics for the PolicyDesk Admin Dashboard."""
    all_docs = document_service.list_documents(db=db, processed_only=False)
    total_docs = len(all_docs)
    processed_docs = sum(1 for d in all_docs if d.processing_status == "processed")
    failed_docs = sum(1 for d in all_docs if d.processing_status == "failed")
    processing_docs = sum(1 for d in all_docs if d.processing_status == "processing")
    total_chunks = db.query(DocumentChunk).count()
    total_users = db.query(User).count()
    total_conversations = db.query(Conversation).count()

    return AdminStatsResponse(
        total_documents=total_docs,
        processed_documents=processed_docs,
        failed_documents=failed_docs,
        processing_documents=processing_docs,
        total_chunks=total_chunks,
        total_users=total_users,
        total_conversations=total_conversations,
        recent_uploads=all_docs[:8],
    )


@router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a PDF or TXT document into the RAG knowledge base",
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> DocumentResponse:
    """
    Validate, extract text, chunk with overlap, embed with Gemini, and store chunks
    in PostgreSQL. Restricted to administrators.
    """
    file_bytes = await file.read()
    return document_service.ingest_document(
        db=db,
        filename=file.filename or "",
        file_bytes=file_bytes,
        content_type=file.content_type,
        uploader=admin_user,
    )


@router.get(
    "/documents",
    response_model=List[DocumentResponse],
    summary="List all uploaded documents (including processing and failed)",
)
def list_admin_documents(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> List[DocumentResponse]:
    """Return all uploaded documents with full metadata and processing status."""
    return document_service.list_documents(db=db, processed_only=False)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Inspect a specific document and its extracted chunks",
)
def get_admin_document_detail(
    document_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> DocumentDetailResponse:
    """Return full document metadata and all extracted text chunks."""
    return document_service.get_document_detail(db=db, document_id=document_id)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document and all associated chunks and embeddings",
)
def delete_admin_document(
    document_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> dict:
    """Permanently delete a document and cascade-delete its chunks and vector embeddings."""
    return document_service.delete_document(db=db, document_id=document_id)


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all registered users",
)
def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> List[UserResponse]:
    """Return all registered users ordered by creation timestamp descending."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserResponse.from_orm(u) for u in users]


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update a user's role or active status",
)
def update_user(
    user_id: int,
    payload: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> UserResponse:
    """Allow an administrator to promote/demote a user or toggle account active status."""
    updated = AuthService.update_user_by_admin(
        db=db,
        target_user_id=user_id,
        payload=payload,
        acting_admin=admin_user,
    )
    return UserResponse.from_orm(updated)
