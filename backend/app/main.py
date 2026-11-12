"""
PolicyDesk FastAPI Application Entrypoint.
Configures CORS, initializes database tables and pgvector extension, runs optional
initial admin seeding from environment variables, and registers all REST routers.
"""
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, init_db
from app.routes import admin, auth, chat, documents, health
from app.seed import seed_accounts_and_sample_data

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Enterprise RAG Document Assistant powered by FastAPI, PostgreSQL + pgvector, "
            "and Google Gemini. Provides role-based document ingestion, overlapping semantic "
            "chunking, vector similarity retrieval, and source-grounded conversational Q&A."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS for Vercel frontend and local Vite development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(documents.router)
    app.include_router(chat.router)

    @app.get("/", tags=["Root"])
    def root() -> dict:
        return {
            "application": settings.APP_NAME,
            "version": "1.0.0",
            "docs_url": "/docs",
            "health_url": "/health",
        }

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()
        if settings.INITIAL_ADMIN_PASSWORD:
            db = SessionLocal()
            try:
                seed_docs = os.getenv("SEED_SAMPLE_DOCS", "false").lower() in (
                    "true",
                    "1",
                    "yes",
                )
                seed_accounts_and_sample_data(db, seed_sample_docs=seed_docs)
            except Exception as exc:
                logger.warning("Startup seed check encountered an issue: %s", exc)
            finally:
                db.close()

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
    )
