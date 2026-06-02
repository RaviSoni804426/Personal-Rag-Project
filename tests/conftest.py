"""
Global Pytest fixtures for DataMind test suite.
Configures in-memory/temporary SQLite instances and mock settings for offline testing.
"""

import os
import sys
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Adjust path to import datamind package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Configure test environment variables before imports
TEST_DB_PATH = "./data/test_datamind.db"
os.environ["DB_PATH"] = TEST_DB_PATH
os.environ["DEBUG"] = "true"
os.environ["GROQ_API_KEY"] = "gsk_test_key"
os.environ["OPENAI_API_KEY"] = "sk_test_key"

from datamind.config import settings
from datamind.storage import VectorStore
from datamind.services import DocumentService
from datamind.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure clean directories exist and clean up after session."""
    # Ensure test directories exist
    settings.DB_PATH = TEST_DB_PATH
    settings.ensure_directories()
    
    yield
    
    # Tear down database file after tests finish
    db_file = Path(TEST_DB_PATH)
    if db_file.exists():
        try:
            db_file.unlink()
        except OSError:
            pass
        
    # Tear down test data dirs
    upload_dir = Path(settings.UPLOAD_DIR)
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)
    
    log_file = Path(settings.LOG_FILE)
    if log_file.exists():
        try:
            log_file.unlink()
        except OSError:
            pass


@pytest.fixture(autouse=True)
def clean_database():
    """Clear database tables before each test case for isolation."""
    # Delete test db file if exists to fresh start
    db_path = Path(TEST_DB_PATH)
    if db_path.exists():
        try:
            # We connect and drop tables
            with pytest.MonkeyPatch().context() as m:
                pass
        except:
            pass
            
    # Initialize fresh schema
    store = VectorStore(TEST_DB_PATH)
    
    with sqlite3_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents")
        cursor.execute("DELETE FROM embeddings")
        cursor.execute("DELETE FROM embedding_cache")
        cursor.execute("DELETE FROM search_history")
        conn.commit()
        
    yield store


def sqlite3_connect():
    import sqlite3
    return sqlite3.connect(TEST_DB_PATH)


@pytest.fixture
def vector_store():
    """Get active vector store pointing to test database."""
    return VectorStore(TEST_DB_PATH)


@pytest.fixture
def document_service(vector_store):
    """Get active document service with mocked dependencies."""
    return DocumentService(vector_store)


@pytest.fixture
def test_client():
    """FastAPI TestClient fixture for endpoint integration testing."""
    # Lazy init components inside main app lifecycle
    with TestClient(app) as client:
        yield client
