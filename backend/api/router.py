import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.document_service import DocumentService
from backend.services.chat_service import ChatService
from backend.config.config import settings

router = APIRouter(prefix="/api")

# Pydantic schemas
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Raw text search query.")
    session_id: str = Field(default="default", description="Conversational session tracker.")
    document_id: Optional[str] = Field(default=None, description="Scope query directly to a specific document.")
    k: int = Field(default=5, ge=1, le=20, description="Retrieve top K records.")

class ChatSource(BaseModel):
    chunk_id: str
    text_content: str
    score: float
    filename: str
    sources: List[str]

class ChatEvaluation(BaseModel):
    faithfulness: float
    context_precision: float
    answer_relevance: float

class QueryResponse(BaseModel):
    answer: str
    confidence: float
    latency_ms: float
    token_usage: int
    sources: List[ChatSource]
    eval_scores: ChatEvaluation

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    chunk_strategy: str
    chunks_count: int
    status: str
    created_at: str

class SystemResetResponse(BaseModel):
    status: str
    message: str

# Endpoints
@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    chunk_strategy: str = Form("recursive"),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    db: Session = Depends(get_db)
):
    # Verify file extensions
    ext = file.filename.split(".")[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported extensions: {settings.ALLOWED_EXTENSIONS}"
        )
        
    # Set up local uploads directory
    upload_dir = "./data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{os.urandom(8).hex()}_{file.filename}")
    
    # Save file securely
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file to local disk: {str(e)}")

    # Ingest document
    try:
        doc_service = DocumentService(db)
        doc = doc_service.ingest_document(
            file_path=file_path,
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        return DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size or 0,
            chunk_strategy=doc.chunk_strategy,
            chunks_count=doc.chunks_count,
            status=doc.status,
            created_at=doc.created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        # Cleanup temporary files on failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Document parsing/indexing failed: {str(e)}")

@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    doc_service = DocumentService(db)
    docs = doc_service.list_documents()
    
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size or 0,
            chunk_strategy=doc.chunk_strategy,
            chunks_count=doc.chunks_count,
            status=doc.status,
            created_at=doc.created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
        for doc in docs
    ]

@router.delete("/documents/{document_id}", response_model=SystemResetResponse)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc_service = DocumentService(db)
    success = doc_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found or delete action failed.")
    return {"status": "success", "message": f"Document {document_id} and its vector indices removed."}

@router.post("/chat", response_model=QueryResponse)
def chat(request: QueryRequest, db: Session = Depends(get_db)):
    try:
        chat_service = ChatService(db)
        result = chat_service.query(
            query=request.query,
            session_id=request.session_id,
            document_id=request.document_id,
            k=request.k
        )
        return QueryResponse(
            answer=result["answer"],
            confidence=result["confidence"],
            latency_ms=result["latency_ms"],
            token_usage=result["token_usage"],
            sources=[
                ChatSource(
                    chunk_id=s["chunk_id"],
                    text_content=s["text_content"],
                    score=s["score"],
                    filename=s["filename"],
                    sources=s["sources"]
                )
                for s in result["sources"]
            ],
            eval_scores=ChatEvaluation(
                faithfulness=result["eval_scores"]["faithfulness"],
                context_precision=result["eval_scores"]["context_precision"],
                answer_relevance=result["eval_scores"]["answer_relevance"]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM query processing failed: {str(e)}")

@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    try:
        # Collect operational metrics
        from backend.database.models import Document, DocumentChunk
        chat_service = ChatService(db)
        
        docs_count = db.query(Document).filter(Document.status == "indexed").count()
        chunks_count = db.query(DocumentChunk).count()
        
        dashboard_metrics = chat_service.get_dashboard_metrics()
        
        # Merge counts
        dashboard_metrics["docs_indexed_count"] = docs_count
        dashboard_metrics["chunks_indexed_count"] = chunks_count
        
        return dashboard_metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch system metrics: {str(e)}")

@router.post("/system/reset", response_model=SystemResetResponse)
def reset_system(db: Session = Depends(get_db)):
    try:
        # 1. Clean up local databases and collections
        from backend.database.models import Document, DocumentChunk, QueryLog, EmbeddingCache
        db.query(DocumentChunk).delete()
        db.query(Document).delete()
        db.query(QueryLog).delete()
        db.query(EmbeddingCache).delete()
        db.commit()
        
        # 2. Reset vector store index
        vector_store = ChromaVectorStore()
        vector_store.reset()
        
        # 3. Purge physical files in local uploads
        upload_dir = "./data/uploads"
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
            os.makedirs(upload_dir, exist_ok=True)
            
        return {"status": "success", "message": "Relational data tables, Vector indices, and physical files purged successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Purge and system resets failed: {str(e)}")
