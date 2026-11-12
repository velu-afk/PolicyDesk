"""
Document Ingestion & Management Service.
Validates uploaded PDF/TXT files, extracts text, generates overlapping chunks,
computes Gemini embeddings, and stores chunks + metadata persistently in PostgreSQL.
Avoids storing uploaded files on Render's ephemeral local filesystem.
"""
import logging
import os
from typing import List, Optional
from fastapi import HTTPException, status

from app.config import settings
from app.database import Session
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.document import (
    DocumentChunkPreview,
    DocumentDetailResponse,
    DocumentResponse,
)
from app.services.embedding_service import embedding_service
from app.services.rag_service import rag_service
from app.utils.text_processing import (
    DocumentProcessingError,
    create_overlapping_chunks,
    extract_text_from_pdf,
    extract_text_from_txt,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf": "pdf", ".txt": "txt"}


class DocumentService:
    """Manages document ingestion, chunking, embedding persistence, and deletion."""

    @staticmethod
    def ingest_document(
        db: Session,
        filename: str,
        file_bytes: bytes,
        content_type: Optional[str],
        uploader: User,
    ) -> DocumentResponse:
        """
        Validate, extract, chunk, embed, and persist a PDF or TXT document.
        Marks document as 'processed' on success or records failure appropriately.
        """
        if not filename or not filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required.",
            )

        clean_filename = os.path.basename(filename.strip())
        _, ext = os.path.splitext(clean_filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{ext or 'unknown'}'. Only .pdf and .txt documents are allowed.",
            )

        file_type = ALLOWED_EXTENSIONS[ext]
        file_size = len(file_bytes) if file_bytes else 0

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes).",
            )

        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )

        # Create initial Document record in 'processing' status
        doc = Document(
            filename=clean_filename,
            file_type=file_type,
            file_size=file_size,
            page_count=1,
            chunk_count=0,
            uploaded_by=uploader.id,
            processing_status="processing",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        try:
            if file_type == "pdf":
                pages, page_count = extract_text_from_pdf(file_bytes)
            else:
                pages, page_count = extract_text_from_txt(file_bytes)

            chunks = create_overlapping_chunks(
                pages=pages,
                filename=clean_filename,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            if not chunks:
                raise DocumentProcessingError(
                    "No meaningful text chunks could be extracted from the document."
                )

            chunk_texts = [c.chunk_text for c in chunks]
            embeddings = embedding_service.embed_batch(
                chunk_texts, task_type="RETRIEVAL_DOCUMENT"
            )

            db_chunks: List[DocumentChunk] = []
            for chunk_item, emb_vec in zip(chunks, embeddings):
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_text=chunk_item.chunk_text,
                    embedding=emb_vec,
                    page_number=chunk_item.page_number,
                    chunk_index=chunk_item.chunk_index,
                    chunk_metadata=chunk_item.metadata,
                )
                db.add(db_chunk)
                db_chunks.append(db_chunk)

            full_text = "\n\n".join(p.text for p in pages)
            doc.page_count = page_count
            doc.chunk_count = len(db_chunks)
            doc.summary = rag_service.generate_document_summary(clean_filename, full_text)
            doc.processing_status = "processed"
            doc.error_message = None

            db.add(doc)
            db.commit()
            db.refresh(doc)

        except DocumentProcessingError as exc:
            doc.processing_status = "failed"
            doc.error_message = str(exc)
            db.add(doc)
            db.commit()
            db.refresh(doc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error during document ingestion: %s", exc)
            doc.processing_status = "failed"
            doc.error_message = f"Processing error: {exc}"
            db.add(doc)
            db.commit()
            db.refresh(doc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process document: {exc}",
            ) from exc

        return DocumentService.to_document_response(db, doc)

    @staticmethod
    def to_document_response(db: Session, doc: Document) -> DocumentResponse:
        uploader_name = None
        if doc.uploaded_by is not None:
            uploader = db.query(User).filter(User.id == doc.uploaded_by).first()
            if uploader is not None:
                uploader_name = uploader.name
        return DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size or 0,
            page_count=doc.page_count,
            chunk_count=doc.chunk_count or 0,
            summary=doc.summary,
            error_message=doc.error_message,
            uploaded_by=doc.uploaded_by,
            uploader_name=uploader_name,
            upload_timestamp=doc.upload_timestamp,
            processing_status=doc.processing_status,
        )

    @staticmethod
    def list_documents(db: Session, processed_only: bool = False) -> List[DocumentResponse]:
        query = db.query(Document)
        if processed_only:
            query = query.filter(Document.processing_status == "processed")
        docs = query.order_by(Document.upload_timestamp.desc()).all()
        return [DocumentService.to_document_response(db, d) for d in docs]

    @staticmethod
    def get_document_detail(db: Session, document_id: int) -> DocumentDetailResponse:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found.",
            )
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        base_resp = DocumentService.to_document_response(db, doc)
        chunk_previews = [
            DocumentChunkPreview(
                id=c.id,
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                chunk_text=c.chunk_text,
                metadata=c.chunk_metadata,
            )
            for c in chunks
        ]
        return DocumentDetailResponse(**base_resp.dict(), chunks=chunk_previews)

    @staticmethod
    def delete_document(db: Session, document_id: int) -> dict:
        """
        Delete a document and ensure all associated DocumentChunk rows and embeddings
        are deleted (both via ORM cascade and explicit cleanup).
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found.",
            )

        filename = doc.filename
        associated_chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .all()
        )
        removed_chunks_count = len(associated_chunks)
        for ch in associated_chunks:
            db.delete(ch)

        db.delete(doc)
        db.commit()

        return {
            "message": f"Document '{filename}' and {removed_chunks_count} associated chunks were permanently deleted.",
            "deleted_document_id": document_id,
            "deleted_chunks_count": removed_chunks_count,
        }


document_service = DocumentService()
