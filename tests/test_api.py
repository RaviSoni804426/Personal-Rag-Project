"""
Integration tests for DataMind FastAPI REST API endpoints.
Tests health checks, document ingestion upload, search, and conversational chat routers.
"""

import io
import pytest
from unittest.mock import patch, MagicMock


def test_api_health_check(test_client):
    """Test standard health check endpoints return expected status codes."""
    res = test_client.get("/api/health/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database_connected" in data
    
    res = test_client.get("/api/health/live")
    assert res.status_code == 200
    assert res.json() == {"alive": True}
    
    res = test_client.get("/api/health/ready")
    assert res.status_code == 200
    assert "ready" in res.json()


def test_upload_document_text(test_client):
    """Test file upload ingest pipelines with a simple plain-text file."""
    # We mock the DocumentService dependency to avoid API calls during REST testing
    with patch('datamind.api.documents.document_service.ingest_document') as mock_ingest:
        mock_ingest.return_value = 42
        
        file_payload = {
            "files": ("mock_doc.txt", io.BytesIO(b"Hello data world context search"), "text/plain")
        }
        
        res = test_client.post(
            "/api/documents/upload",
            files=file_payload,
            data={"doc_type": "text"}
        )
        
        assert res.status_code == 200
        # If successful, should return DocumentInfo
        data = res.json()
        assert data["filename"] == "mock_doc.txt"
        assert data["doc_type"] == "text"


def test_search_documents_endpoint(test_client):
    """Test vector similarity search API parameters and outputs."""
    with patch('datamind.api.documents.document_service.search') as mock_search:
        from datamind.models import SearchResult
        
        mock_search.return_value = [
            SearchResult(
                id=1,
                text="Matching segment context.",
                filename="doc1.txt",
                doc_type="text",
                similarity_score=0.88,
                metadata={"chunk_index": 0},
                excerpt="Matching segment..."
            )
        ]
        
        search_req = {
            "query": "Where is data world?",
            "top_k": 3,
            "similarity_threshold": 0.0
        }
        
        res = test_client.post("/api/documents/search", json=search_req)
        
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "Where is data world?"
        assert data["total_results"] == 1
        assert data["results"][0]["filename"] == "doc1.txt"
        assert data["results"][0]["similarity_score"] == 0.88


def test_chat_conversational_endpoint(test_client):
    """Test AI chat response syntheses and context arrays."""
    with patch('datamind.api.chat.document_service.get_answer') as mock_get_answer:
        from datamind.models import SearchResult
        
        mock_get_answer.return_value = {
            "query": "Hello",
            "answer": "This is synthetic response context.",
            "context": "Context block info.",
            "retrieved": [
                SearchResult(
                    id=2,
                    text="Segment text retrieved.",
                    filename="doc2.txt",
                    doc_type="text",
                    similarity_score=0.92,
                    metadata={"chunk_index": 2},
                    excerpt="Segment text..."
                )
            ],
            "llm_available": True,
            "llm_provider": "openai"
        }
        
        chat_req = {
            "message": "Hello",
            "top_k": 3
        }
        
        res = test_client.post("/api/chat/", json=chat_req)
        
        assert res.status_code == 200
        data = res.json()
        assert data["user_message"] == "Hello"
        assert data["assistant_response"] == "This is synthetic response context."
        assert len(data["retrieved_context"]) == 1
        assert data["retrieved_context"][0]["filename"] == "doc2.txt"
        assert "openai" in data["model_used"]
