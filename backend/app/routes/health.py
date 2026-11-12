"""
Health check endpoint for Render deployment probes and monitoring:
- GET /health
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from app.config import settings
from app.database import PGVECTOR_AVAILABLE, Session, get_db, is_sqlite, text

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service and database health check")
def health_check(db: Session = Depends(get_db)) -> dict:
    """Verify API readiness, database connectivity, and configured Gemini model names."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": {
            "status": db_status,
            "engine": "sqlite" if is_sqlite else "postgresql",
            "pgvector_enabled": PGVECTOR_AVAILABLE and not is_sqlite,
        },
        "ai_models": {
            "llm_model": settings.GEMINI_LLM_MODEL,
            "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
            "embedding_dimensions": settings.GEMINI_EMBEDDING_DIMENSIONS,
            "similarity_threshold": settings.SIMILARITY_THRESHOLD,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
