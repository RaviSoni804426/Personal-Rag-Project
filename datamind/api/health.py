"""
API routes for system health and status.
"""

from fastapi import APIRouter
from datetime import datetime

from datamind.models import HealthResponse
from datamind.core import get_embeddings_service, get_llm_service
from datamind.storage import VectorStore
from datamind.config import settings
from datamind.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Check system health and service availability."""
    try:
        embeddings_service = get_embeddings_service()
        llm_service = get_llm_service()
        
        # Check database
        try:
            vector_store = VectorStore(settings.DB_PATH)
            db_connected = True
        except:
            db_connected = False
        
        # Check embeddings service
        embeddings_available = embeddings_service.verify_connection()
        
        # Check LLM service
        llm_available = llm_service.verify_connection() if llm_service.available else False
        
        status = "healthy" if (db_connected and embeddings_available) else "degraded"
        
        return HealthResponse(
            status=status,
            version=settings.API_VERSION,
            database_connected=db_connected,
            embeddings_service_available=embeddings_available,
            llm_service_available=llm_available,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            version=settings.API_VERSION,
            database_connected=False,
            embeddings_service_available=False,
            llm_service_available=False,
            timestamp=datetime.now()
        )


@router.get("/ready")
async def readiness_check():
    """Check if service is ready to serve requests."""
    try:
        embeddings_service = get_embeddings_service()
        embeddings_available = embeddings_service.verify_connection()
        
        if embeddings_available:
            return {"ready": True, "message": "Service is ready"}
        else:
            return {"ready": False, "message": "Embeddings service unavailable"}
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"ready": False, "message": str(e)}


@router.get("/live")
async def liveness_check():
    """Check if service is running."""
    return {"alive": True}
