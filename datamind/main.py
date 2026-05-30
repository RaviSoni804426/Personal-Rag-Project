"""
DataMind - Intelligent Document Intelligence Platform
Main FastAPI application
"""

# Load environment variables FIRST before any other imports
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from datamind.config import settings
from datamind.utils import get_logger, setup_logging
from datamind.core import get_embeddings_service, get_llm_service
from datamind.storage import VectorStore
from datamind.services import DocumentService
from datamind.api import documents_router, chat_router, health_router

logger = setup_logging()


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("=" * 60)
    logger.info(f"DataMind {settings.API_VERSION} starting up...")
    logger.info(f"Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    logger.info(f"Database: {settings.DB_PATH}")
    logger.info(f"Model: {settings.EMBEDDING_MODEL}")
    
    # Ensure directories exist
    settings.ensure_directories()
    
    # Initialize vector store and document service
    try:
        vector_store = VectorStore(settings.DB_PATH)
        document_service = DocumentService(vector_store)
        
        # Set them in the API modules so routes can use them
        import datamind.api.documents
        import datamind.api.chat
        datamind.api.documents.vector_store = vector_store
        datamind.api.documents.document_service = document_service
        datamind.api.chat.vector_store = vector_store
        datamind.api.chat.document_service = document_service
        
        logger.info("[OK] Vector store and document service initialized")
    except Exception as e:
        logger.error(f"[FAILED] Vector store initialization failed: {e}")
        raise
    
    # Verify services
    try:
        embeddings = get_embeddings_service()
        logger.info("[OK] Embeddings service initialized")
    except Exception as e:
        logger.error(f"[FAILED] Embeddings service failed: {e}")
    
    try:
        llm = get_llm_service()
        if llm.available:
            logger.info("[OK] LLM service initialized")
        else:
            logger.warning("[WARN] LLM service disabled (no OpenAI or Groq key set)")
    except Exception as e:
        logger.error(f"[FAILED] LLM service initialization failed: {e}")
    
    logger.info("=" * 60)
    logger.info("Application ready to serve requests")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("DataMind shutting down...")
    logger.info("=" * 60)


# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    description="Enterprise-grade document intelligence and semantic search platform",
    version=settings.API_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests."""
    start_time = datetime.now()
    response = await call_next(request)
    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
    
    # Log to console (structured logging would be better in production)
    log_level = "INFO" if response.status_code < 400 else "WARNING" if response.status_code < 500 else "ERROR"
    logger.log(
        getattr(__import__("logging"), log_level),
        f"{request.method} {request.url.path} - {response.status_code} ({elapsed_ms:.2f}ms)"
    )
    
    return response


# Include API routers
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(chat_router)


# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Root endpoint - serve UI
@app.get("/")
async def root():
    """Serve the web UI."""
    ui_path = os.path.join(static_dir, "index.html")
    if os.path.exists(ui_path):
        return FileResponse(ui_path)
    return {
        "message": "DataMind - Intelligent Document Intelligence Platform",
        "version": settings.API_VERSION,
        "docs": "/api/docs",
        "health": "/api/health"
    }


# API info endpoint
@app.get("/api")
async def api_info():
    """Get API information."""
    return {
        "name": "DataMind API",
        "version": settings.API_VERSION,
        "description": "Intelligent document intelligence and semantic search platform",
        "endpoints": {
            "documents": "/api/documents",
            "chat": "/api/chat",
            "health": "/api/health",
            "docs": "/api/docs"
        }
    }


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.DEBUG else "An error occurred"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        workers=1,  # Single worker for development
        log_level=settings.LOG_LEVEL.lower()
    )
