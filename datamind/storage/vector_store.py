"""
Vector storage and retrieval layer for DataMind.
Handles embedding storage in SQLite with similarity search.
"""

import json
import sqlite3
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import numpy as np

from datamind.utils import get_logger

logger = get_logger(__name__)


class VectorStore:
    """SQLite-based vector store for document embeddings and retrieval."""

    def __init__(self, db_path: str = "./data/datamind.db"):
        """Initialize vector store."""
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create database schema if not exists."""
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
                
                # Embeddings table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        doc_id INTEGER NOT NULL,
                        embedding TEXT NOT NULL,
                        chunk_index INTEGER DEFAULT 0,
                        FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
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
                
                # Create indexes for performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_filename 
                    ON documents(filename)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_embeddings_doc_id 
                    ON embeddings(doc_id)
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
        
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def add_document(
        self,
        filename: str,
        text: str,
        embedding: List[float],
        doc_type: str = "text",
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """
        Add a document with embeddings to the store.
        
        Returns: Document ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert document
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
                
                # Insert embedding
                cursor.execute("""
                    INSERT INTO embeddings (doc_id, embedding, chunk_index)
                    VALUES (?, ?, ?)
                """, (doc_id, json.dumps(embedding), 0))
                
                conn.commit()
                logger.info(f"Document added: {filename} (ID: {doc_id})")
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
        
        Each document dict should have: filename, text, embedding, doc_type (optional), metadata (optional), tags (optional)
        
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
                    tags=doc.get("tags")
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
        threshold: float = 0.0
    ) -> List[Dict]:
        """
        Perform similarity search on embeddings.
        
        Returns: List of similar documents with scores
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all documents with embeddings
                cursor.execute("""
                    SELECT d.id, d.filename, d.doc_type, d.text, d.metadata, e.embedding
                    FROM documents d
                    JOIN embeddings e ON d.id = e.doc_id
                    ORDER BY d.created_at DESC
                """)
                
                rows = cursor.fetchall()
                
                if not rows:
                    return []
                
                # Calculate similarity scores
                q_emb = np.array(query_embedding, dtype=np.float32)
                results = []
                
                for row in rows:
                    doc_id, filename, doc_type, text, metadata_str, emb_str = row
                    embedding = np.array(json.loads(emb_str), dtype=np.float32)
                    
                    # Cosine similarity
                    similarity = self._cosine_similarity(q_emb, embedding)
                    
                    if similarity >= threshold:
                        results.append({
                            "id": doc_id,
                            "filename": filename,
                            "doc_type": doc_type,
                            "text": text,
                            "metadata": json.loads(metadata_str or "{}"),
                            "score": float(similarity)
                        })
                
                # Sort by score and return top_k
                results.sort(key=lambda x: x["score"], reverse=True)
                return results[:top_k]
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def get_document(self, doc_id: int) -> Optional[Dict]:
        """Retrieve a specific document by ID."""
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
                
                return {
                    "id": row[0],
                    "filename": row[1],
                    "doc_type": row[2],
                    "text": row[3],
                    "metadata": json.loads(row[4] or "{}"),
                    "tags": json.loads(row[5] or "[]"),
                    "created_at": row[6]
                }
        
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            raise

    def get_all_documents(self) -> List[Dict]:
        """Get all documents."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, filename, doc_type, text, metadata, tags, created_at
                    FROM documents
                    ORDER BY created_at DESC
                """)
                
                rows = cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "filename": row[1],
                        "doc_type": row[2],
                        "text": row[3],
                        "metadata": json.loads(row[4] or "{}"),
                        "tags": json.loads(row[5] or "[]"),
                        "created_at": row[6]
                    }
                    for row in rows
                ]
        
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            raise

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document."""
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
        """Get storage statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total documents
                cursor.execute("SELECT COUNT(*) FROM documents")
                total_docs = cursor.fetchone()[0]
                
                # Total embeddings
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
            logger.error(f"Failed to get stats: {e}")
            raise

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
