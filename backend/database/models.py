import datetime
import json
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database.connection import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(50), primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=True)
    file_size = Column(Integer, nullable=True)
    chunk_strategy = Column(String(50), default="recursive")
    chunks_count = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # pending, processing, indexed, failed
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def get_metadata(self):
        try:
            return json.loads(self.metadata_json or "{}")
        except Exception:
            return {}

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(String(100), primary_key=True)
    document_id = Column(String(50), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    parent_chunk_id = Column(String(100), nullable=True)  # For parent-child chunk relations
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")

    def get_metadata(self):
        try:
            return json.loads(self.metadata_json or "{}")
        except Exception:
            return {}

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    token_usage = Column(Integer, default=0)
    retrieved_chunks = Column(Text, default="[]")  # JSON string of source info
    
    # Evaluation Metrics
    faithfulness_score = Column(Float, nullable=True)
    context_precision_score = Column(Float, nullable=True)
    answer_relevance_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def get_sources(self):
        try:
            return json.loads(self.retrieved_chunks or "[]")
        except Exception:
            return []

class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    
    text_hash = Column(String(64), primary_key=True)  # SHA-256 hash of text
    embedding_json = Column(Text, nullable=False)    # JSON representation of float list
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
