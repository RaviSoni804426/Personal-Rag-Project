"""
API routes for chat and conversational AI.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid

from datamind.services import DocumentService
from datamind.models import ConversationMessage, ConversationResponse, SearchResult
from datamind.storage import VectorStore
from datamind.utils import get_logger
from datamind.config import settings

logger = get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


# Global service instances (initialized in main.py lifespan)
vector_store = None
document_service = None


@router.post("/", response_model=ConversationResponse)
async def chat(request: ConversationMessage):
    """Process user message and generate response."""
    try:
        start_time = datetime.now()
        message_id = str(uuid.uuid4())
        # Ensure document_service is available (lazily initialize if needed)
        global document_service, vector_store
        if document_service is None:
            try:
                vector_store = VectorStore(settings.DB_PATH)
                document_service = DocumentService(vector_store)
            except Exception as e:
                logger.error(f"Failed to initialize document service: {e}")
                raise

        # Get answer with context retrieval
        result = document_service.get_answer(
            query=request.message,
            top_k=request.top_k,
            system_prompt=request.system_prompt,
        )
        
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return ConversationResponse(
            message_id=message_id,
            user_message=request.message,
            assistant_response=result["answer"],
            retrieved_context=result["retrieved"],
            context_count=len(result["retrieved"]),
            response_time_ms=elapsed_ms,
            model_used=f"{settings.EMBEDDING_MODEL} + {result.get('llm_provider') or 'retrieval-only'}"
        )
    
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed")


@router.post("/stream")
async def chat_stream(request: ConversationMessage):
    """Stream chat response (placeholder for future implementation)."""
    raise HTTPException(
        status_code=501,
        detail="Streaming not yet implemented. Use /chat endpoint."
    )
