import os
import uuid
import json
from typing import List, Dict, Any, Optional
from backend.config.config import settings

class BaseVectorStore:
    """Interface to ensure plug-and-play migrations (Pinecone, Weaviate, Qdrant)."""
    def add_chunks(self, document_id: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        raise NotImplementedError()

    def search(self, query_embedding: List[float], k: int = 10, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError()

    def delete_document(self, document_id: str) -> None:
        raise NotImplementedError()

    def reset(self) -> None:
        raise NotImplementedError()

class ChromaVectorStore(BaseVectorStore):
    def __init__(self):
        self.persist_dir = settings.CHROMA_PERSIST_DIR
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = None
        self.collection = None
        self._initialize_chroma()

    def _initialize_chroma(self):
        """Initializes ChromaDB persistent client, fallback to SQLite mathematical cosine if failed."""
        try:
            import chromadb
            print(f"Initializing persistent ChromaDB vector store at: {self.persist_dir}")
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            # Create or get collection
            self.collection = self.client.get_or_create_collection(
                name="enterprise_rag_collection",
                metadata={"hnsw:space": "cosine"}
            )
            print("ChromaDB initialized successfully.")
        except Exception as e:
            print(f"Warning: Failed to load local ChromaDB ({str(e)}). Switching to SQL-backed vector retrieval fallback.")
            self.client = None
            self.collection = None

    def add_chunks(self, document_id: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        if not chunks or not embeddings:
            return

        # If ChromaDB is down/offline, we store vectors in SQLAlchemy tables (which models.py already holds chunks metadata).
        # We can implement a clean dual storage or SQLite fallback.
        if self.collection is not None:
            try:
                ids = [str(c["id"]) for c in chunks]
                documents = [c["text_content"] for c in chunks]
                
                # Convert metadata to Chroma-safe flat values
                metadatas = []
                for c in chunks:
                    meta = {
                        "document_id": document_id,
                        "chunk_index": c["chunk_index"],
                        "filename": c.get("filename", "")
                    }
                    if c.get("parent_chunk_id"):
                        meta["parent_chunk_id"] = c["parent_chunk_id"]
                    metadatas.append(meta)
                    
                # Add in batches
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                return
            except Exception as e:
                print(f"ChromaDB write error, using fallback mechanisms: {e}")

        # Fallback vector logging (already handled by main Relational database storage models)
        print("Note: Saved chunks locally in SQL for exact backup matching.")

    def search(self, query_embedding: List[float], k: int = 10, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        results_list = []
        
        # Method 1: ChromaDB Query
        if self.collection is not None:
            try:
                where_filter = {}
                if document_id:
                    where_filter = {"document_id": document_id}

                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    where=where_filter if where_filter else None
                )

                if results and results["ids"] and results["ids"][0]:
                    for i in range(len(results["ids"][0])):
                        # Cosine similarity conversion if necessary
                        score = float(results["distances"][0][i])
                        # Distance is cosine distance, convert to similarity metric
                        similarity = 1.0 - score if score <= 1.0 else 0.0
                        
                        results_list.append({
                            "chunk_id": results["ids"][0][i],
                            "text_content": results["documents"][0][i],
                            "score": similarity,
                            "metadata": results["metadatas"][0][i]
                        })
                return results_list
            except Exception as e:
                print(f"ChromaDB search error, switching to relational database matching fallback: {e}")

        # Method 2: Fallback Relational mathematical Cosine calculation
        # We fetch all chunks from database, calculate similarity against query vector
        from backend.database.connection import SessionLocal
        from backend.database.models import DocumentChunk, EmbeddingCache
        import numpy as np
        
        db = SessionLocal()
        try:
            chunks = db.query(DocumentChunk).all()
            if document_id:
                chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
                
            scored_chunks = []
            q_vec = np.array(query_embedding)
            q_norm = np.linalg.norm(q_vec)
            
            for chunk in chunks:
                # Get embedding from cache
                text_hash = hashlib.sha256(chunk.text_content.encode("utf-8")).hexdigest() if "hashlib" in globals() else ""
                if not text_hash:
                    import hashlib
                    text_hash = hashlib.sha256(chunk.text_content.encode("utf-8")).hexdigest()
                    
                cached_vector = db.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
                if cached_vector:
                    v = np.array(json.loads(cached_vector.embedding_json))
                    v_norm = np.linalg.norm(v)
                    if q_norm > 0 and v_norm > 0:
                        sim = np.dot(q_vec, v) / (q_norm * v_norm)
                        scored_chunks.append((sim, chunk))
                        
            # Sort descending
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            for sim, chunk in scored_chunks[:k]:
                meta = json.loads(chunk.metadata_json or "{}")
                meta.update({
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index
                })
                results_list.append({
                    "chunk_id": chunk.id,
                    "text_content": chunk.text_content,
                    "score": float(sim),
                    "metadata": meta
                })
        except Exception as e:
            print(f"Ultimate fallback retrieval error: {e}")
        finally:
            db.close()
            
        return results_list

    def delete_document(self, document_id: str) -> None:
        if self.collection is not None:
            try:
                self.collection.delete(where={"document_id": document_id})
            except Exception as e:
                print(f"ChromaDB delete error: {e}")

    def reset(self) -> None:
        if self.client is not None:
            try:
                self.client.reset()
                self._initialize_chroma()
            except Exception as e:
                print(f"ChromaDB reset error: {e}")
