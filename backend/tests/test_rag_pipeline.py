import os
import json
import pytest
from sqlalchemy.orm import Session
from backend.database.connection import engine, Base, SessionLocal
from backend.database.models import Document, DocumentChunk, EmbeddingCache
from backend.ingestion.loaders import TextLoader, BaseLoader
from backend.chunking.strategies import RecursiveCharacterChunker, ParentChildChunker, SemanticSimilarityChunker
from backend.embeddings.provider import EmbeddingProvider
from backend.database.vector_store import ChromaVectorStore
from backend.retrieval.hybrid import HybridRetriever
from backend.reranking.reranker import CrossEncoderReranker
from backend.evaluation.metrics import RAGEvaluator

@pytest.fixture(scope="module")
def setup_db():
    # Sync testing database schemas
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_document_loader():
    # Write a temporary text file
    temp_file = "./temp_test.txt"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write("Welcome to the Enterprise Knowledge Intelligence Platform. RAG is awesome!")
        
    loader = TextLoader(temp_file)
    text, meta = loader.load()
    
    assert "Enterprise Knowledge" in text
    assert meta["file_type"] == "txt"
    
    if os.path.exists(temp_file):
        os.remove(temp_file)

def test_chunking_recursive():
    text = "Line 1.\nLine 2.\nLine 3. This is a sentence about AI Architectures."
    chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=5)
    splits = chunker.chunk(text)
    
    assert len(splits) > 0
    assert any("AI Architectures" in s for s in splits)

def test_chunking_parent_child():
    text = "Parent blocks are very large sections of text that can represent paragraphs. Child blocks are smaller subsections."
    chunker = ParentChildChunker(parent_size=80, child_size=30, overlap=5)
    relations = chunker.chunk(text)
    
    assert len(relations) > 0
    assert "parent_text" in relations[0]
    assert "child_text" in relations[0]

def test_embedding_caching(setup_db):
    db = setup_db
    provider = EmbeddingProvider()
    
    text = "Test persistent hash caching block."
    # Run once to vectorize
    vec1 = provider.embed_query(text)
    
    # Check if hash entry is saved in database cache
    import hashlib
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    cached = db.query(EmbeddingCache).filter(EmbeddingCache.text_hash == text_hash).first()
    
    assert cached is not None
    assert len(json.loads(cached.embedding_json)) == len(vec1)

def test_hybrid_rrf_search(setup_db):
    db = setup_db
    # Ingest mock chunks into DB
    doc_id = "test_doc_01"
    
    doc = Document(id=doc_id, filename="test_doc.txt", chunk_strategy="recursive", status="indexed")
    db.add(doc)
    
    chunks = [
        DocumentChunk(id="c1", document_id=doc_id, chunk_index=0, text_content="The quick brown fox jumps over the lazy dog."),
        DocumentChunk(id="c2", document_id=doc_id, chunk_index=1, text_content="AI engineers build state of the art software tools."),
        DocumentChunk(id="c3", document_id=doc_id, chunk_index=2, text_content="Data science requires intensive mathematical statistics.")
    ]
    db.add_all(chunks)
    db.commit()
    
    vector_store = ChromaVectorStore()
    provider = EmbeddingProvider()
    
    # Load index mock items into Vector Database fallback list
    embs = provider.embed_texts([c.text_content for c in chunks])
    vector_store.add_chunks(doc_id, [{"id": c.id, "text_content": c.text_content, "chunk_index": c.chunk_index} for c in chunks], embs)
    
    retriever = HybridRetriever(vector_store, provider)
    # Search term matching 'software tools'
    hits = retriever.retrieve("software tools", k=2)
    
    assert len(hits) > 0
    # The first hit should highly relate to chunk 2 (AI engineers build software) due to BM25 + Dense overlap
    assert "AI engineers" in hits[0]["text_content"]

def test_cross_encoder_rerank():
    reranker = CrossEncoderReranker()
    chunks = [
        {"chunk_id": "1", "text_content": "The weather is sunny in California.", "rrf_score": 0.5},
        {"chunk_id": "2", "text_content": "Next.js is a premium React framework developed by Vercel.", "rrf_score": 0.3}
    ]
    
    # Reranking against 'React frameworks'
    sorted_hits = reranker.rerank("React frameworks", chunks, top_n=1)
    assert len(sorted_hits) == 1
    assert "Next.js" in sorted_hits[0]["text_content"]

def test_rag_evaluator():
    evaluator = RAGEvaluator()
    
    # 1. Retrieval eval
    ret_ids = ["c1", "c2", "c3"]
    gt_ids = ["c2", "c4"]
    ret_stats = evaluator.evaluate_retrieval(ret_ids, gt_ids, k=2)
    
    assert ret_stats["precision_at_k"] == 0.5
    assert ret_stats["recall_at_k"] == 0.5
    assert ret_stats["mrr"] == 0.5  # hit at index 1 (rank 2)
    
    # 2. Answer faithfulness overlap checks
    ctx = ["ChromaDB is a local vector database.", "Groq runs high performance LLM speeds."]
    ans = "ChromaDB acts as a local vector database storage layer."
    
    scores = evaluator.evaluate_generation("What is ChromaDB?", ctx, ans)
    assert scores["faithfulness"] > 0.5
    assert scores["answer_relevance"] > 0.5
