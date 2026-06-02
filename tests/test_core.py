"""
Unit tests for Core Services layer.
Tests EmbeddingsService caching, local models fallback, and LLMService.
"""

import pytest
from unittest.mock import patch, MagicMock
from datamind.core.embeddings import EmbeddingsService
from datamind.core.llm import LLMService


def test_local_embeddings_generation():
    """Verify that local offline model generates deterministic, normalized vectors."""
    service = EmbeddingsService(api_key=None)  # Forces local mode
    
    vector1 = service.embed_text("DeepMind AI is leading agentic coding.")
    vector2 = service.embed_text("DeepMind AI is leading agentic coding.")
    vector3 = service.embed_text("Different query for similarity tests.")
    
    assert len(vector1) == 1536
    # Deterministic check
    assert vector1 == vector2
    # Non-identical check
    assert vector1 != vector3
    
    # Normalized check: norm should be close to 1.0
    import numpy as np
    norm = np.linalg.norm(vector1)
    assert abs(norm - 1.0) < 1e-5


@patch('requests.post')
def test_groq_api_embeddings_batch(mock_post):
    """Test standard API batch requests to Groq embeddings endpoints."""
    # Simulate API success response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"embedding": [0.1] * 1536},
            {"embedding": [0.2] * 1536}
        ]
    }
    mock_post.return_value = mock_response
    
    service = EmbeddingsService(api_key="gsk_test_key")
    assert service.local_mode is False
    
    results = service._embed_batch(["text 1", "text 2"])
    
    assert len(results) == 2
    assert results[0] == [0.1] * 1536
    assert results[1] == [0.2] * 1536
    assert mock_post.called


def test_persistent_cache_hits(vector_store):
    """Test that EmbeddingsService utilizes the SQLite cache table transparently."""
    service = EmbeddingsService(api_key=None)
    
    test_text = "Transparent caching tests."
    
    # 1st call: Misses cache, generates locally, writes to cache
    with patch.object(service, '_embed_locally', return_type=list, side_effect=service._embed_locally) as mock_local:
        vec1 = service.embed_text(test_text)
        assert mock_local.call_count == 1
        
    # 2nd call: Hits persistent cache instantly, does not call _embed_locally!
    with patch.object(service, '_embed_locally') as mock_local:
        vec2 = service.embed_text(test_text)
        assert mock_local.call_count == 0  # Resolved via cache!
        assert vec1 == vec2


def test_llm_service_degradation():
    """Test LLMService graceful degradation when no keys are configured."""
    service = LLMService(api_key=None)
    assert service.available is False
    
    # When unavailable, verify that it falls back to context fragment snippets
    response = service.generate_response(
        query="Explain agentic coding",
        context="Agentic coding enables models to act independently to solve problems."
    )
    
    assert "I couldn't reach an LLM provider" in response
    assert "Agentic coding enables" in response


@patch('requests.post')
def test_llm_api_call_succeeds(mock_post):
    """Test active API execution paths in LLMService."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "DataMind is a professional document platform."
                }
            }
        ]
    }
    mock_post.return_value = mock_response
    
    service = LLMService(api_key="sk_test_key")
    assert service.available is True
    
    response = service.generate_response(
        query="What is DataMind?",
        context="DataMind is a document intelligence platform."
    )
    
    assert response == "DataMind is a professional document platform."
    assert mock_post.called
