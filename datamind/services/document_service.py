"""
Document service for processing and managing documents.
"""

from typing import List, Optional, Dict, Any
import time
from pathlib import Path

from datamind.core import get_embeddings_service, get_llm_service
from datamind.storage import VectorStore
from datamind.models import SearchResult, ConversationResponse, DocumentInfo
from datamind.utils import get_logger, extract_text_from_file, chunk_text
from datamind.config import settings

logger = get_logger(__name__)


class DocumentService:
    """Service for document processing and management."""

    def __init__(self, vector_store: VectorStore):
        """Initialize document service."""
        self.vector_store = vector_store
        self.embeddings = get_embeddings_service()
        self.llm = get_llm_service()

    def ingest_document(
        self,
        filename: str,
        content: str,
        doc_type: str = "text",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Ingest a document and generate embeddings.
        
        Returns: Document ID
        """
        try:
            logger.info(f"Ingesting document: {filename}")
            
            # Generate embeddings
            embedding = self.embeddings.embed_text(content)
            
            # Store in vector store
            doc_id = self.vector_store.add_document(
                filename=filename,
                text=content,
                embedding=embedding,
                doc_type=doc_type,
                metadata=metadata,
                tags=tags or []
            )
            
            logger.info(f"Document ingested successfully: {filename} (ID: {doc_id})")
            return doc_id
        
        except Exception as e:
            logger.error(f"Document ingestion failed: {e}")
            raise

    def ingest_file(
        self,
        filepath: str,
        doc_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Ingest a file by extracting text and creating document.
        
        Returns: Document ID
        """
        try:
            filepath = str(filepath)
            filename = Path(filepath).name
            
            # Extract text from file
            text = extract_text_from_file(filepath)
            if not text:
                raise ValueError(f"Could not extract text from {filename}")
            
            # Determine doc type if not provided
            if not doc_type:
                doc_type = Path(filepath).suffix.lstrip(".").lower()
            
            return self.ingest_document(
                filename=filename,
                content=text,
                doc_type=doc_type,
                tags=tags,
                metadata=metadata
            )
        
        except Exception as e:
            logger.error(f"File ingestion failed: {e}")
            raise

    def ingest_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Ingest multiple documents in batch.
        
        Each document should have: filename, content (or filepath), doc_type (optional), tags (optional), metadata (optional)
        """
        doc_ids = []
        for doc in documents:
            try:
                if "filepath" in doc:
                    doc_id = self.ingest_file(
                        filepath=doc["filepath"],
                        doc_type=doc.get("doc_type"),
                        tags=doc.get("tags"),
                        metadata=doc.get("metadata")
                    )
                else:
                    doc_id = self.ingest_document(
                        filename=doc.get("filename", "document"),
                        content=doc["content"],
                        doc_type=doc.get("doc_type", "text"),
                        tags=doc.get("tags"),
                        metadata=doc.get("metadata")
                    )
                doc_ids.append(doc_id)
            except Exception as e:
                logger.warning(f"Failed to ingest document: {e}")
                continue
        
        return doc_ids

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Search for documents similar to query.
        
        Returns: List of search results
        """
        try:
            start_time = time.time()
            
            # Use defaults if not specified
            top_k = top_k or settings.DEFAULT_TOP_K
            top_k = min(top_k, settings.MAX_TOP_K)
            threshold = threshold or settings.SIMILARITY_THRESHOLD
            
            # Generate query embedding
            query_embedding = self.embeddings.embed_text(query)
            
            # Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                threshold=threshold
            )
            
            # Convert to SearchResult models
            search_results = []
            for result in results:
                search_result = SearchResult(
                    id=result["id"],
                    text=result["text"],
                    filename=result["filename"],
                    doc_type=result["doc_type"],
                    similarity_score=result["score"],
                    metadata=result["metadata"],
                    excerpt=result["text"][:200] + "..."
                )
                search_results.append(search_result)
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"Search completed in {elapsed_ms:.2f}ms with {len(search_results)} results")
            
            return search_results
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def get_answer(
        self,
        query: str,
        top_k: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an answer to a query using retrieved context and LLM.
        
        Returns: Dictionary with query, answer, and retrieved context
        """
        try:
            # Search for relevant documents
            search_results = self.search(query, top_k=top_k)
            
            if not search_results:
                return {
                    "query": query,
                    "answer": None,
                    "context": "No relevant documents found.",
                    "retrieved": [],
                    "llm_available": False,
                    "llm_provider": None
                }
            
            # Build context from search results
            context = "\n\n---\n\n".join([
                f"[{r.filename}]\n{r.text[:500]}..."
                for r in search_results
            ])
            
            # Generate answer using LLM
            answer = None
            if self.llm.available:
                answer = self.llm.generate_response(
                    query=query,
                    context=context,
                    system_prompt=system_prompt
                )
            
            return {
                "query": query,
                "answer": answer,
                "context": context,
                "retrieved": search_results,
                "llm_available": self.llm.available,
                "llm_provider": "openai" if self.llm.openai_api_key else "groq" if self.llm.groq_api_key else None
            }
        
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            raise

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document."""
        return self.vector_store.delete_document(doc_id)

    def get_document(self, doc_id: int) -> Optional[DocumentInfo]:
        """Get document information."""
        doc = self.vector_store.get_document(doc_id)
        if not doc:
            return None
        
        return DocumentInfo(
            id=doc["id"],
            filename=doc["filename"],
            text=doc["text"],
            doc_type=doc["doc_type"],
            tags=doc.get("tags", []),
            metadata=doc.get("metadata", {}),
            created_at=doc["created_at"],
            char_count=len(doc["text"]),
            chunk_count=1
        )

    def get_all_documents(self) -> List[DocumentInfo]:
        """Get all documents."""
        docs = self.vector_store.get_all_documents()
        return [
            DocumentInfo(
                id=doc["id"],
                filename=doc["filename"],
                text=doc["text"],
                doc_type=doc["doc_type"],
                tags=doc.get("tags", []),
                metadata=doc.get("metadata", {}),
                created_at=doc["created_at"],
                char_count=len(doc["text"]),
                chunk_count=1
            )
            for doc in docs
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get storage and indexing statistics."""
        return self.vector_store.get_stats()
