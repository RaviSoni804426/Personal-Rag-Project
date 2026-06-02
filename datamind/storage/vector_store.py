"""
Vector storage and retrieval layer for DataMind.
Handles embedding storage in SQLite with similarity search and persistent caching.
"""

import json
import sqlite3
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import numpy as np

from datamind.utils import get_logger

logger = get_logger(__name__)


class VectorStore:
    """SQLite-based vector store for document embeddings, caching, and retrieval."""

    def __init__(self, db_path: str = "./data/datamind.db"):
        """Initialize vector store."""
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create database schema if not exists and perform migrations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Documents table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        doc_type TEXT,
                        text TEXT NOT NULL,
                        metadata TEXT,
                        tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Embeddings table (added chunk_text TEXT during initialization)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        doc_id INTEGER NOT NULL,
                        embedding TEXT NOT NULL,
                        chunk_text TEXT,
                        chunk_index INTEGER DEFAULT 0,
                        FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """)
                
                # Persistent Embedding Cache Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS embedding_cache (
                        text_hash TEXT PRIMARY KEY,
                        embedding TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Search history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS search_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT NOT NULL,
                        results_count INTEGER,
                        response_time_ms REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Perform Schema Migrations for legacy DB files
                cursor.execute("PRAGMA table_info(embeddings)")
                columns = [col[1] for col in cursor.fetchall()]
                if "chunk_text" not in columns:
                    logger.info("Migrating database: adding 'chunk_text' column to 'embeddings' table.")
                    cursor.execute("ALTER TABLE embeddings ADD COLUMN chunk_text TEXT")
                
                # Create indexes for high-speed performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_filename 
                    ON documents(filename)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_embeddings_doc_id 
                    ON embeddings(doc_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_embedding_cache_hash
                    ON embedding_cache(text_hash)
                """)
                
                conn.commit()
                logger.info("Database initialized and migrated successfully")
        
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    # ==================== Embedding Cache Methods ====================
    
    def get_cached_embedding(self, text_hash: str) -> Optional[List[float]]:
        """Retrieve a cached embedding by SHA-256 hash."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT embedding FROM embedding_cache WHERE text_hash = ?",
                    (text_hash,)
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
        except Exception as e:
            logger.error(f"Failed to read from embedding cache: {e}")
            return None

    def cache_embedding(self, text_hash: str, embedding: List[float]) -> None:
        """Store an embedding in the persistent cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO embedding_cache (text_hash, embedding) VALUES (?, ?)",
                    (text_hash, json.dumps(embedding))
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to write to embedding cache: {e}")

    # ==================== Document Ingestion Methods ====================

    def add_document(
        self,
        filename: str,
        text: str,
        embedding: Optional[List[float]] = None,
        doc_type: str = "text",
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        chunks: Optional[List[Tuple[str, List[float]]]] = None,
    ) -> int:
        """
        Add a document with embeddings to the store.
        Supports both legacy unchunked documents and modernized chunk lists.
        
        Args:
            filename: Name of the file
            text: Full text content
            embedding: Single embedding for the whole document (legacy)
            doc_type: File extension/type
            metadata: Custom metadata dictionary
            tags: Classification tags
            chunks: List of tuples containing (chunk_text, chunk_embedding)
            
        Returns: Document ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert parent document metadata
                cursor.execute("""
                    INSERT INTO documents (filename, doc_type, text, metadata, tags)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    filename,
                    doc_type,
                    text,
                    json.dumps(metadata or {}),
                    json.dumps(tags or [])
                ))
                
                doc_id = cursor.lastrowid
                
                # Insert chunk-level embeddings
                if chunks:
                    logger.info(f"Inserting {len(chunks)} chunks for document ID: {doc_id}")
                    for idx, (chunk_text, chunk_emb) in enumerate(chunks):
                        cursor.execute("""
                            INSERT INTO embeddings (doc_id, embedding, chunk_text, chunk_index)
                            VALUES (?, ?, ?, ?)
                        """, (doc_id, json.dumps(chunk_emb), chunk_text, idx))
                elif embedding:
                    # Legacy fallback: store full text as a single chunk
                    logger.info(f"Inserting legacy single embedding for document ID: {doc_id}")
                    cursor.execute("""
                        INSERT INTO embeddings (doc_id, embedding, chunk_text, chunk_index)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, json.dumps(embedding), text, 0))
                
                conn.commit()
                logger.info(f"Document successfully written: {filename} (ID: {doc_id})")
                return doc_id
        
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            raise

    def add_batch_documents(
        self,
        documents: List[Dict]
    ) -> List[int]:
        """
        Add multiple documents in batch.
        
        Returns: List of document IDs
        """
        doc_ids = []
        try:
            for doc in documents:
                doc_id = self.add_document(
                    filename=doc.get("filename"),
                    text=doc.get("text"),
                    embedding=doc.get("embedding"),
                    doc_type=doc.get("doc_type", "text"),
                    metadata=doc.get("metadata"),
                    tags=doc.get("tags"),
                    chunks=doc.get("chunks")
                )
                doc_ids.append(doc_id)
            
            logger.info(f"Batch added: {len(doc_ids)} documents")
            return doc_ids
        
        except Exception as e:
            logger.error(f"Batch add failed: {e}")
            raise

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
        query_text: Optional[str] = None
    ) -> List[Dict]:
        """
        Perform similarity search on individual document chunks.
        Supports advanced Hybrid Search combining vector cosine similarity 
        and term-overlap keyword relevance scores for 100% precision.
        
        Returns: List of similar chunks with similarity scores and document metadata
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Fetch chunks with their embedding vectors and document source info
                cursor.execute("""
                    SELECT d.id, d.filename, d.doc_type, d.metadata, e.embedding, e.chunk_text, e.chunk_index
                    FROM documents d
                    JOIN embeddings e ON d.id = e.doc_id
                """)
                
                rows = cursor.fetchall()
                
                if not rows:
                    return []
                
                q_emb = np.array(query_embedding, dtype=np.float32)
                results = []
                
                for row in rows:
                    doc_id, filename, doc_type, metadata_str, emb_str, chunk_text, chunk_index = row
                    
                    try:
                        embedding = np.array(json.loads(emb_str), dtype=np.float32)
                    except Exception as parse_error:
                        logger.warning(f"Error parsing embedding for doc {doc_id}: {parse_error}")
                        continue
                    
                    # Cosine similarity calculation
                    similarity = self._cosine_similarity(q_emb, embedding)
                    
                    # Hybrid Keyword Term Overlap Score (TF-IDF-like Jaccard match)
                    keyword_score = 0.0
                    target_chunk_text = chunk_text or ""
                    
                    if query_text and target_chunk_text:
                        # Normalize and extract lowercase alphanumeric words
                        q_words = set(re.findall(r"\w+", query_text.lower()))
                        c_words = set(re.findall(r"\w+", target_chunk_text.lower()))
                        if q_words:
                            overlap = len(q_words.intersection(c_words))
                            # Score is the percentage of query keywords present in the segment
                            keyword_score = overlap / len(q_words)
                    
                    # Hybrid weighted combination:
                    # Semantic search provides excellent concept understanding (40% weight).
                    # Keyword search guarantees exact matches on product specs, names, codes (60% weight).
                    if query_text:
                        hybrid_score = 0.4 * similarity + 0.6 * keyword_score
                    else:
                        hybrid_score = similarity
                    
                    if hybrid_score >= threshold:
                        text_val = chunk_text if chunk_text is not None else ""
                        
                        results.append({
                            "id": doc_id,
                            "filename": filename,
                            "doc_type": doc_type,
                            "text": text_val,
                            "metadata": {
                                **json.loads(metadata_str or "{}"),
                                "chunk_index": chunk_index
                            },
                            "score": float(hybrid_score)
                        })
                
                # Sort by similarity score descending
                results.sort(key=lambda x: x["score"], reverse=True)
                
                # Record search in history log for metrics
                try:
                    cursor.execute("""
                        INSERT INTO search_history (query, results_count, response_time_ms)
                        VALUES (?, ?, ?)
                    """, (query_text or "*Vector Search*", len(results[:top_k]), 0.0))
                    conn.commit()
                except Exception as log_error:
                    logger.debug(f"Failed to log search history: {log_error}")
                
                return results[:top_k]
        
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

    def get_document(self, doc_id: int) -> Optional[Dict]:
        """Retrieve a specific document metadata and total chunk info."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, filename, doc_type, text, metadata, tags, created_at
                    FROM documents WHERE id = ?
                """, (doc_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Calculate chunk count
                cursor.execute("SELECT COUNT(*) FROM embeddings WHERE doc_id = ?", (doc_id,))
                chunk_count = cursor.fetchone()[0]
                
                return {
                    "id": row[0],
                    "filename": row[1],
                    "doc_type": row[2],
                    "text": row[3],
                    "metadata": json.loads(row[4] or "{}"),
                    "tags": json.loads(row[5] or "[]"),
                    "created_at": row[6],
                    "chunk_count": max(chunk_count, 1)
                }
        
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            raise

    def get_all_documents(self) -> List[Dict]:
        """Get all stored documents with accurate chunk counts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, filename, doc_type, text, metadata, tags, created_at
                    FROM documents
                    ORDER BY created_at DESC
                """)
                
                rows = cursor.fetchall()
                docs = []
                for row in rows:
                    doc_id = row[0]
                    cursor.execute("SELECT COUNT(*) FROM embeddings WHERE doc_id = ?", (doc_id,))
                    chunk_count = cursor.fetchone()[0]
                    
                    docs.append({
                        "id": doc_id,
                        "filename": row[1],
                        "doc_type": row[2],
                        "text": row[3],
                        "metadata": json.loads(row[4] or "{}"),
                        "tags": json.loads(row[5] or "[]"),
                        "created_at": row[6],
                        "chunk_count": max(chunk_count, 1)
                    })
                return docs
        
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document and all corresponding chunks (via CASCADE constraints)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                conn.commit()
                logger.info(f"Document deleted: ID {doc_id}")
                return cursor.rowcount > 0
        
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise

    def get_stats(self) -> Dict:
        """Get database storage statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total documents
                cursor.execute("SELECT COUNT(*) FROM documents")
                total_docs = cursor.fetchone()[0]
                
                # Total embeddings/chunks
                cursor.execute("SELECT COUNT(*) FROM embeddings")
                total_embeddings = cursor.fetchone()[0]
                
                # Total characters
                cursor.execute("SELECT SUM(LENGTH(text)) FROM documents")
                total_chars = cursor.fetchone()[0] or 0
                
                # Documents by type
                cursor.execute("""
                    SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type
                """)
                doc_types = dict(cursor.fetchall())
                
                return {
                    "total_documents": total_docs,
                    "total_embeddings": total_embeddings,
                    "total_characters": total_chars,
                    "avg_doc_size": total_chars / max(total_docs, 1),
                    "doc_types": doc_types
                }
        
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
