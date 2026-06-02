"""
Document service for processing, chunking, and managing documents.
Provides complete RAG execution pathways.
"""

from typing import List, Optional, Dict, Any
import time
from pathlib import Path

from datamind.core import get_embeddings_service, get_llm_service
from datamind.storage import VectorStore
from datamind.models import SearchResult, DocumentInfo
from datamind.utils import get_logger, extract_text_from_file, chunk_text
from datamind.config import settings

logger = get_logger(__name__)


class DocumentService:
    """Service for orchestrating document ingestion, semantic chunking, and RAG pipelines."""

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
        Ingest a document, split it into semantic chunks, and store their vector representations.
        
        Returns: Document ID
        """
        try:
            logger.info(f"Ingesting document: {filename} ({len(content)} characters)")
            
            # Divide document content into standard overlapping chunks
            chunks_list = chunk_text(content, chunk_size=500, overlap=100)
            if not chunks_list:
                chunks_list = [content] if content.strip() else ["(Empty Document)"]
            
            logger.info(f"Chunking yielded {len(chunks_list)} segments for {filename}")
            
            # Batch-request embedding vectors for all segments
            embeddings = self.embeddings.embed_texts(chunks_list)
            
            # Construct tuples of (segment_text, segment_vector)
            chunk_data = list(zip(chunks_list, embeddings))
            
            # Store parent document metadata and segment embeddings in VectorStore
            doc_id = self.vector_store.add_document(
                filename=filename,
                text=content,
                doc_type=doc_type,
                metadata=metadata or {},
                tags=tags or [],
                chunks=chunk_data
            )
            
            logger.info(f"Document ingestion complete: {filename} (ID: {doc_id})")
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
        Ingest a file by extracting text and creating a chunked document.
        
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
                logger.warning(f"Failed to ingest document in batch: {e}")
                continue
        
        return doc_ids

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Search for document segments similar to the query.
        
        Returns: List of segment search results
        """
        try:
            start_time = time.time()
            
            # Fall back to defaults if parameters are omitted
            top_k = top_k or settings.DEFAULT_TOP_K
            top_k = min(top_k, settings.MAX_TOP_K)
            threshold = threshold or settings.SIMILARITY_THRESHOLD
            
            # Generate vector representation for the search query (hits cache if identical to prior query)
            query_embedding = self.embeddings.embed_text(query)
            
            # Perform similarity search across individual stored segments
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                threshold=threshold
            )
            
            # Convert DB matches to schema SearchResult models
            search_results = []
            for result in results:
                # Truncate clean excerpt for visual representations
                clean_text = result["text"]
                excerpt = clean_text[:200] + "..." if len(clean_text) > 200 else clean_text
                
                search_result = SearchResult(
                    id=result["id"],
                    text=clean_text,
                    filename=result["filename"],
                    doc_type=result["doc_type"],
                    similarity_score=result["score"],
                    metadata=result["metadata"],
                    excerpt=excerpt
                )
                search_results.append(search_result)
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"Vector search done in {elapsed_ms:.2f}ms. Found {len(search_results)} matching segments.")
            
            return search_results
        
        except Exception as e:
            logger.error(f"Search query processing failed: {e}")
            raise

    def get_answer(
        self,
        query: str,
        top_k: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize an answer using similar document segments and LLM generation.
        
        Returns: Dict containing prompt query, generated synthesis, and retrieved context segments
        """
        try:
            # Retrieve segments most similar to the query
            search_results = self.search(query, top_k=top_k)
            
            if not search_results:
                return {
                    "query": query,
                    "answer": "No relevant documents found. Please upload documents first.",
                    "context": "No relevant document segments retrieved.",
                    "retrieved": [],
                    "llm_available": False,
                    "llm_provider": None
                }
            
            # Merge context chunks into prompt format
            context_blocks = []
            for idx, result in enumerate(search_results):
                chunk_index = result.metadata.get("chunk_index", 0)
                context_blocks.append(
                    f"[{idx + 1}] Source File: {result.filename} | Segment Index: {chunk_index}\n"
                    f"Content: {result.text}"
                )
            
            context = "\n\n---\n\n".join(context_blocks)
            
            # Request LLM synthesis based on context
            answer = None
            if self.llm.available:
                answer = self.llm.generate_response(
                    query=query,
                    context=context,
                    system_prompt=system_prompt
                )
            
            # Fall back to localized context display if API keys are absent
            if not answer:
                answer = self.llm._fallback_response(query, context)
            
            return {
                "query": query,
                "answer": answer,
                "context": context,
                "retrieved": search_results,
                "llm_available": self.llm.available,
                "llm_provider": "openai" if self.llm.openai_api_key else "groq" if self.llm.groq_api_key else None
            }
        
        except Exception as e:
            logger.error(f"Failed to generate synthesis answer: {e}")
            raise

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document."""
        return self.vector_store.delete_document(doc_id)

    def get_document(self, doc_id: int) -> Optional[DocumentInfo]:
        """Get document details."""
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
            chunk_count=doc.get("chunk_count", 1)
        )

    def get_all_documents(self) -> List[DocumentInfo]:
        """Get all stored documents."""
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
                chunk_count=doc.get("chunk_count", 1)
            )
            for doc in docs
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get database indexing and storage statistics."""
        return self.vector_store.get_stats()
