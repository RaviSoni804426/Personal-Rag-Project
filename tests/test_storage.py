"""
Unit tests for VectorStore storage layer.
Tests schema creation, caching, segment additions, and cosine calculations.
"""

import pytest
import numpy as np
from datamind.storage import VectorStore


def test_database_initialization(vector_store):
    """Test that schema tables and indexes are successfully created."""
    assert vector_store is not None
    stats = vector_store.get_stats()
    assert stats["total_documents"] == 0
    assert stats["total_embeddings"] == 0


def test_add_unchunked_document(vector_store):
    """Test legacy backward-compatible document insertion (single embedding)."""
    mock_embedding = [0.1] * 1536
    doc_id = vector_store.add_document(
        filename="legacy.txt",
        text="This is a legacy text without segment chunks.",
        embedding=mock_embedding,
        doc_type="txt",
        metadata={"author": "Staff Architect"},
        tags=["legacy", "test"]
    )
    
    assert doc_id > 0
    doc = vector_store.get_document(doc_id)
    assert doc is not None
    assert doc["filename"] == "legacy.txt"
    assert doc["doc_type"] == "txt"
    assert doc["metadata"]["author"] == "Staff Architect"
    assert "legacy" in doc["tags"]
    assert doc["chunk_count"] == 1


def test_add_chunked_document(vector_store):
    """Test modernized segment chunk ingestion."""
    chunks = [
        ("This is segment chunk number one.", [0.1] * 1536),
        ("This is segment chunk number two.", [0.2] * 1536)
    ]
    
    doc_id = vector_store.add_document(
        filename="chunked.pdf",
        text="This is segment chunk number one. This is segment chunk number two.",
        doc_type="pdf",
        metadata={"subject": "Advanced RAG"},
        tags=["chunked", "pdf"],
        chunks=chunks
    )
    
    assert doc_id > 0
    doc = vector_store.get_document(doc_id)
    assert doc is not None
    assert doc["chunk_count"] == 2
    
    # Verify stats
    stats = vector_store.get_stats()
    assert stats["total_documents"] == 1
    assert stats["total_embeddings"] == 2


def test_cosine_similarity():
    """Verify accuracy of vector cosine calculation helper."""
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    c = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    
    # Identical vectors should have similarity of 1.0
    assert abs(VectorStore._cosine_similarity(a, b) - 1.0) < 1e-6
    # Orthogonal vectors should have similarity of 0.0
    assert abs(VectorStore._cosine_similarity(a, c) - 0.0) < 1e-6


def test_similarity_search(vector_store):
    """Verify retrieval search returns closest matching segments."""
    # Insert two target chunks
    chunks_1 = [("Pineapples grow on shrubs.", [1.0, 0.0, 0.0] + [0.0] * 1533)]
    chunks_2 = [("Automobiles run on gasoline.", [0.0, 1.0, 0.0] + [0.0] * 1533)]
    
    vector_store.add_document("fruits.txt", "Pineapples grow on shrubs.", doc_type="txt", chunks=chunks_1)
    vector_store.add_document("cars.txt", "Automobiles run on gasoline.", doc_type="txt", chunks=chunks_2)
    
    # Query vector close to fruits (1.0, 0.0, 0.0...)
    query_emb = [0.9, 0.1, 0.0] + [0.0] * 1533
    results = vector_store.search(query_emb, top_k=2)
    
    assert len(results) == 2
    assert results[0]["filename"] == "fruits.txt"  # Closest match
    assert "Pineapples" in results[0]["text"]
    assert results[0]["score"] > results[1]["score"]


def test_persistent_embedding_cache(vector_store):
    """Test that embedding hashes are cached and resolved correctly."""
    text_hash = "mock_sha256_hash_value"
    mock_vector = [0.55] * 1536
    
    # Initially missing
    cached = vector_store.get_cached_embedding(text_hash)
    assert cached is None
    
    # Store in cache
    vector_store.cache_embedding(text_hash, mock_vector)
    
    # Should hit cache now
    cached = vector_store.get_cached_embedding(text_hash)
    assert cached is not None
    assert abs(cached[0] - 0.55) < 1e-6


def test_cascade_delete_document(vector_store):
    """Test that deleting a document cleans up all segment embeddings too."""
    chunks = [
        ("Chunk segment 1", [0.1] * 1536),
        ("Chunk segment 2", [0.2] * 1536)
    ]
    doc_id = vector_store.add_document("delete_test.txt", "Chunk segment 1 Chunk segment 2", chunks=chunks)
    
    stats = vector_store.get_stats()
    assert stats["total_documents"] == 1
    assert stats["total_embeddings"] == 2
    
    # Delete document
    success = vector_store.delete_document(doc_id)
    assert success is True
    
    # Verify stats are empty now due to cascade deletions
    stats = vector_store.get_stats()
    assert stats["total_documents"] == 0
    assert stats["total_embeddings"] == 0
