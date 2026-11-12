"""
Vector Similarity Retrieval Service.
Queries stored DocumentChunk embeddings using pgvector cosine distance on PostgreSQL
or exact cosine similarity on SQLite, applying a configurable similarity threshold.
"""
from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.database import PGVECTOR_AVAILABLE, SQLALCHEMY_NATIVE, Session, is_sqlite
from app.models.document import Document, DocumentChunk
from app.services.embedding_service import embedding_service


@dataclass
class RetrievedChunkResult:
    """Represents a retrieved document chunk along with its source document and similarity score."""

    chunk_id: int
    document_id: int
    document_name: str
    chunk_text: str
    page_number: Optional[int]
    chunk_index: int
    metadata: Optional[Dict[str, Any]]
    similarity_score: float


def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute exact cosine similarity between two vectors in [-1.0, 1.0]."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


class RetrievalService:
    """Performs semantic vector search over processed document chunks."""

    @staticmethod
    def retrieve_relevant_chunks(
        db: Session,
        question: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        document_ids: Optional[List[int]] = None,
    ) -> Tuple[List[RetrievedChunkResult], int, Optional[float]]:
        """
        Embed the user's question and retrieve up to `top_k` chunks whose cosine
        similarity meets or exceeds `similarity_threshold`.
        Never returns unrelated chunks below threshold just to fill `top_k`.

        Returns:
            (filtered_results, total_chunks_evaluated, highest_similarity_score)
        """
        k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K
        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else settings.SIMILARITY_THRESHOLD
        )

        query_embedding = embedding_service.embed_text(
            question, task_type="RETRIEVAL_QUERY"
        )

        # Fetch processed documents map
        doc_query = db.query(Document).filter(Document.processing_status == "processed")
        if document_ids:
            doc_query = doc_query.filter(Document.id.in_(document_ids))
        processed_docs = doc_query.all()
        if not processed_docs:
            return [], 0, None

        doc_map: Dict[int, Document] = {d.id: d for d in processed_docs}
        valid_doc_ids = list(doc_map.keys())

        # Path A: Native PostgreSQL + pgvector cosine_distance operator (<=>)
        if not is_sqlite and PGVECTOR_AVAILABLE and SQLALCHEMY_NATIVE:
            distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding).label(
                "distance"
            )
            total_chunks = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id.in_(valid_doc_ids))
                .count()
            )
            rows = (
                db.query(DocumentChunk, distance_expr)
                .filter(DocumentChunk.document_id.in_(valid_doc_ids))
                .order_by(distance_expr)
                .limit(k * 2)
                .all()
            )
            scored_results: List[RetrievedChunkResult] = []
            top_score: Optional[float] = None
            for chunk, distance in rows:
                similarity = round(max(0.0, 1.0 - float(distance)), 4)
                if top_score is None or similarity > top_score:
                    top_score = similarity
                if similarity >= threshold:
                    doc = doc_map.get(chunk.document_id)
                    if doc is not None:
                        scored_results.append(
                            RetrievedChunkResult(
                                chunk_id=chunk.id,
                                document_id=doc.id,
                                document_name=doc.filename,
                                chunk_text=chunk.chunk_text,
                                page_number=chunk.page_number,
                                chunk_index=chunk.chunk_index,
                                metadata=chunk.chunk_metadata,
                                similarity_score=similarity,
                            )
                        )
            return scored_results[:k], total_chunks, top_score

        # Path B: Exact Cosine Similarity over stored chunk vectors
        candidate_chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id.in_(valid_doc_ids))
            .all()
        )
        total_chunks = len(candidate_chunks)
        if total_chunks == 0:
            return [], 0, None

        all_scored: List[RetrievedChunkResult] = []
        top_score = None
        for chunk in candidate_chunks:
            chunk_vec = chunk.embedding or []
            similarity = round(compute_cosine_similarity(query_embedding, chunk_vec), 4)
            if top_score is None or similarity > top_score:
                top_score = similarity
            if similarity >= threshold:
                doc = doc_map.get(chunk.document_id)
                if doc is not None:
                    all_scored.append(
                        RetrievedChunkResult(
                            chunk_id=chunk.id,
                            document_id=doc.id,
                            document_name=doc.filename,
                            chunk_text=chunk.chunk_text,
                            page_number=chunk.page_number,
                            chunk_index=chunk.chunk_index,
                            metadata=chunk.chunk_metadata,
                            similarity_score=similarity,
                        )
                    )

        all_scored.sort(key=lambda r: r.similarity_score, reverse=True)
        return all_scored[:k], total_chunks, top_score


retrieval_service = RetrievalService()
