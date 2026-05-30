"""
API routes for document operations.
"""

from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from datetime import datetime
import io

from PyPDF2 import PdfReader
import docx

from datamind.services import DocumentService
from datamind.models import (
    DocumentUploadRequest,
    SearchRequest,
    SearchResponse,
    SearchResult,
    DocumentInfo,
    DocumentStats
)
from datamind.storage import VectorStore
from datamind.utils import get_logger, is_valid_file_extension, extract_text_from_file
from datamind.config import settings

logger = get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


# Global service instances (initialized in main.py lifespan)
vector_store = None
document_service = None


@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    files: List[UploadFile] = File(...),
    doc_type: str = "document"
):
    """Upload and ingest documents."""
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        doc_ids = []
        for file in files:
            # Validate file type
            if not is_valid_file_extension(file.filename):
                logger.warning(f"Invalid file type: {file.filename}")
                continue
            
            # Read file content
            content = await file.read()

            # Extract text according to file type
            try:
                text = _extract_upload_text(file.filename, content)
            except Exception as extract_error:
                logger.error(f"Could not extract text from {file.filename}: {extract_error}")
                continue
            
            if not text or not text.strip():
                logger.warning(f"Empty document: {file.filename}")
                continue
            
            # Ingest document
            try:
                doc_id = document_service.ingest_document(
                    filename=file.filename,
                    content=text,
                    doc_type=doc_type,
                    metadata={"size": len(content)}
                )
                doc_ids.append(doc_id)
            except Exception as e:
                logger.error(f"Failed to ingest {file.filename}: {e}")
                continue
        
        if not doc_ids:
            raise HTTPException(
                status_code=400,
                detail="No documents could be processed"
            )
        
        # Return first document info
        doc = document_service.get_document(doc_ids[0])
        return doc
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Document upload failed")


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search documents by semantic similarity."""
    try:
        start_time = datetime.now()
        
        results = document_service.search(
            query=request.query,
            top_k=request.top_k,
            threshold=request.similarity_threshold
        )
        
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            search_time_ms=elapsed_ms,
            model_name=settings.EMBEDDING_MODEL
        )
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/", response_model=List[DocumentInfo])
async def list_documents():
    """List all documents."""
    try:
        return document_service.get_all_documents()
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/stats", response_model=DocumentStats)
async def get_stats():
    """Get document statistics."""
    try:
        stats = document_service.get_stats()
        return DocumentStats(
            total_documents=stats["total_documents"],
            total_text_chunks=stats["total_embeddings"],
            total_characters=stats["total_characters"],
            avg_document_size=stats["avg_doc_size"],
            document_types=stats["doc_types"],
            last_updated=datetime.now()
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get("/{doc_id}", response_model=DocumentInfo)
async def get_document(doc_id: int):
    """Get specific document."""
    try:
        doc = document_service.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document")


@router.delete("/{doc_id}")
async def delete_document(doc_id: int):
    """Delete a document."""
    try:
        if not document_service.delete_document(doc_id):
            raise HTTPException(status_code=404, detail="Document not found")
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


def _extract_upload_text(filename: str, content: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if ext == "docx":
        document = docx.Document(io.BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    return content.decode("utf-8")
