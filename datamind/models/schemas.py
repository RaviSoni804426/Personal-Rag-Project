"""
Data models and schemas for DataMind application.
Uses Pydantic for request/response validation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ==================== Request Models ====================


class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""

    filename: str = Field(..., description="Name of the document")
    content: str = Field(..., description="Document content or text")
    doc_type: Optional[str] = Field("text", description="Document type (pdf, docx, txt, etc.)")
    tags: Optional[List[str]] = Field(default_factory=list, description="Document tags for classification")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class SearchRequest(BaseModel):
    """Request model for semantic search."""

    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to retrieve")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity score")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata filters")


class ConversationMessage(BaseModel):
    """Request model for chat/conversation."""

    message: str = Field(..., min_length=1, description="User message")
    top_k: int = Field(5, ge=1, le=20, description="Number of context documents to retrieve")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context tracking")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")


class DocumentBatchRequest(BaseModel):
    """Request model for batch document processing."""

    documents: List[DocumentUploadRequest] = Field(..., min_items=1, description="List of documents to process")
    force_reindex: Optional[bool] = Field(False, description="Force reindexing of documents")


# ==================== Response Models ====================


class DocumentInfo(BaseModel):
    """Information about a stored document."""

    id: int
    filename: str
    text: str
    doc_type: str
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    char_count: int
    chunk_count: int


class SearchResult(BaseModel):
    """Single search result."""

    id: int
    text: str
    filename: str
    doc_type: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}
    excerpt: str = Field("", description="First 200 characters of text")


class SearchResponse(BaseModel):
    """Response model for search results."""
    
    model_config = ConfigDict(protected_namespaces=())

    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    model_name: str = "embed-1"


class ConversationResponse(BaseModel):
    """Response model for conversation."""
    
    model_config = ConfigDict(protected_namespaces=())

    message_id: str
    user_message: str
    assistant_response: Optional[str] = None
    retrieved_context: List[SearchResult]
    context_count: int
    response_time_ms: float
    model_used: str


class DocumentStats(BaseModel):
    """Statistics about stored documents."""

    total_documents: int
    total_text_chunks: int
    total_characters: int
    avg_document_size: float
    document_types: Dict[str, int] = {}
    last_updated: datetime


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    database_connected: bool
    embeddings_service_available: bool
    llm_service_available: bool
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None
    timestamp: datetime
    request_id: Optional[str] = None


# ==================== Internal Models ====================


class VectorDocument(BaseModel):
    """Internal representation of a vectorized document."""

    id: int
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]
    score: Optional[float] = None  # Similarity score after search
