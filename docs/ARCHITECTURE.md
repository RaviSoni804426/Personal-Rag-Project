# DataMind - Architecture Guide

## System Overview

DataMind is built on a modular, production-grade architecture that separates concerns and enables scalability.

```
┌─────────────────────────────────────────────────────────┐
│                     Web UI (React/JS)                   │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/JSON
┌────────────────────▼────────────────────────────────────┐
│              FastAPI Application Layer                  │
├─────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│ │ Documents    │ │ Chat         │ │ Health Check     │ │
│ │ API Routes   │ │ API Routes   │ │ API Routes       │ │
│ └──────┬───────┘ └──────┬───────┘ └──────────────────┘ │
└────────┼──────────────────┼───────────────────────────────┘
         │                  │
         ▼                  ▼
┌──────────────────────────────────────────────────────────┐
│            Business Logic Services Layer                │
├──────────────────────────────────────────────────────────┤
│           Document Service (datamind/services/)         │
│ - Document ingestion & preprocessing                     │
│ - Search orchestration                                   │
│ - Answer generation coordination                         │
└────┬───────────────────────────────────────────────────┬─┘
     │                                                   │
     ▼                                                   ▼
┌──────────────────────┐                   ┌──────────────────────┐
│  Core Services Layer │                   │  Storage Layer       │
├──────────────────────┤                   ├──────────────────────┤
│ EmbeddingsService    │                   │ VectorStore          │
│ - Groq API Client    │                   │ - SQLite Database    │
│ - Text Embedding     │                   │ - Vector Index       │
│ - Batch Processing   │                   │ - Document Retrieval │
│                      │                   │ - Analytics          │
│ LLMService           │                   │                      │
│ - OpenAI Integration │                   │                      │
│ - Response Generation│                   │                      │
└──────────┬───────────┘                   └──────────────────────┘
           │
           ▼
    ┌──────────────────┐
    │  External APIs   │
    ├──────────────────┤
    │ - Groq           │
    │ - OpenAI         │
    └──────────────────┘
```

## Module Organization

### `datamind/config/`
**Responsibility**: Configuration management

- `settings.py`: Centralized settings from environment variables
- Database paths, API keys, performance parameters
- Settings validation on startup

```python
from datamind.config import settings

api_key = settings.GROQ_API_KEY
db_path = settings.DB_PATH
```

### `datamind/models/`
**Responsibility**: Data validation and serialization

- Pydantic models for all API requests/responses
- Type-safe data structures
- Automatic validation and JSON serialization

```python
from datamind.models import SearchRequest, SearchResponse

# Input validation
search_req = SearchRequest(query="...", top_k=5)

# Response serialization
response = SearchResponse(
    query="...",
    results=[...],
    search_time_ms=45.2
)
```

### `datamind/core/`
**Responsibility**: Core AI/ML services

#### `embeddings.py` - EmbeddingsService
- Integrates with Groq API for text embeddings
- Batch processing capabilities
- Error handling and connection verification
- Generates vector representations for semantic search

```python
from datamind.core import get_embeddings_service

embeddings_svc = get_embeddings_service()
vectors = embeddings_svc.embed_texts(["text1", "text2"])
```

#### `llm.py` - LLMService
- OpenAI GPT integration for response generation
- System prompt customization
- Optional service (graceful degradation if not configured)
- Generates intelligent answers from context

```python
from datamind.core import get_llm_service

llm_svc = get_llm_service()
answer = llm_svc.generate_response(query="...", context="...")
```

### `datamind/storage/`
**Responsibility**: Data persistence layer

#### `vector_store.py` - VectorStore
- SQLite-based vector storage
- Document and embedding management
- Similarity search with cosine similarity
- Statistics and analytics queries

```python
from datamind.storage import VectorStore

store = VectorStore("./data/datamind.db")
doc_id = store.add_document(
    filename="document.pdf",
    text="...",
    embedding=[...],
    metadata={...}
)
results = store.search(query_embedding=[...], top_k=5)
```

**Database Schema**:
```
documents:
  id, filename, doc_type, text, metadata, tags, created_at, updated_at

embeddings:
  id, doc_id, embedding, chunk_index

search_history:
  id, query, results_count, response_time_ms, created_at
```

### `datamind/services/`
**Responsibility**: Business logic orchestration

#### `document_service.py` - DocumentService
- High-level document operations
- Coordinates between embeddings and storage
- Implements search and Q&A workflows
- Provides a clean service interface

```python
from datamind.services import DocumentService

doc_svc = DocumentService(vector_store)

# Ingest
doc_id = doc_svc.ingest_document(
    filename="...",
    content="...",
    doc_type="pdf"
)

# Search
results = doc_svc.search(query="...", top_k=5)

# Q&A
answer_data = doc_svc.get_answer(query="...")
```

### `datamind/api/`
**Responsibility**: HTTP API endpoints

#### `documents.py`
- Document upload (`POST /api/documents/upload`)
- Document search (`POST /api/documents/search`)
- Document listing/retrieval (`GET /api/documents/`, `GET /api/documents/{id}`)
- Document deletion (`DELETE /api/documents/{id}`)
- Statistics (`GET /api/documents/stats`)

#### `chat.py`
- Conversation endpoint (`POST /api/chat/`)
- Returns: user message, AI response, retrieved context, metadata

#### `health.py`
- Health checks (`GET /api/health/`)
- Readiness probe (`GET /api/health/ready`)
- Liveness probe (`GET /api/health/live`)

### `datamind/utils/`
**Responsibility**: Helper utilities

- `logging.py`: Structured logging configuration
- `helpers.py`: Text processing, file handling, utility functions

### `datamind/static/`
**Responsibility**: Web UI assets

- `index.html`: Main UI structure
- `style.css`: Professional styling
- `app.js`: Client-side application logic

### `datamind/main.py`
**Responsibility**: FastAPI application entry point

- Application initialization
- Route registration
- Middleware setup (CORS, logging)
- Startup/shutdown event handlers
- Static file serving

## Data Flow

### Document Ingestion Flow

```
┌─────────────┐
│ File Upload │
└─────┬───────┘
      │
      ▼
┌──────────────────┐
│ Text Extraction  │  Extract text from PDF/DOCX/etc
└──────┬───────────┘
       │
       ▼
┌──────────────────────┐
│ Embeddings Service   │  Generate vector representation
│ (Groq API)           │
└──────┬───────────────┘
       │
       ▼
┌─────────────────────┐
│ VectorStore         │  Store document + embeddings
│ (SQLite)            │
└──────┬──────────────┘
       │
       ▼
┌──────────────────────┐
│ UI Updated           │  Show success, refresh stats
└──────────────────────┘
```

### Search Flow

```
┌─────────────┐
│ Query       │
└─────┬───────┘
      │
      ▼
┌──────────────────────┐
│ Embeddings Service   │  Convert query to vector
│ (Groq API)           │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ VectorStore.search() │  Find similar documents
│ (Cosine Similarity)  │  (Top-K retrieval)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Results Ranked       │  Sort by similarity score
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Return to Client     │
└──────────────────────┘
```

### Q&A Flow

```
┌─────────────┐
│ User Query  │
└─────┬───────┘
      │
      ▼
┌──────────────────────┐
│ DocumentService      │
│ .get_answer()        │
└──────┬───────────────┘
       │
       ├─────────────────────────────────┐
       │                                 │
       ▼                                 ▼
┌──────────────┐              ┌──────────────────┐
│ Search       │              │ LLM Service      │
│ (Get Context)│              │ (OpenAI API)     │
└──────┬───────┘              └──────┬───────────┘
       │                             │
       │    Context ◄───────────────┘
       │    + Query
       │
       ▼
┌─────────────────────────┐
│ LLM generates answer    │
│ based on context        │
└──────┬──────────────────┘
       │
       ▼
┌──────────────────────┐
│ ConversationResponse │
│ (answer + context)   │
└──────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API Framework** | FastAPI 0.104.1 | High-performance async web framework |
| **Server** | Uvicorn 0.24.0 | ASGI server |
| **Embeddings** | Groq API | Vector embeddings generation |
| **LLM** | OpenAI GPT-4 | Response generation (optional) |
| **Database** | SQLite 3 | Document and metadata storage |
| **Vectorization** | NumPy 1.24.3 | Vector operations |
| **Validation** | Pydantic 2.5.0 | Data validation |
| **HTTP** | Requests 2.31.0 | API calls |
| **Frontend** | Vanilla JS + CSS | Interactive UI |
| **Containerization** | Docker | Deployment |

## Performance Considerations

### Search Performance
- **Index Type**: Linear scan with cosine similarity
- **Complexity**: O(n) where n = number of documents
- **Optimization**: Can add FAISS indexing for larger datasets
- **Typical Query Time**: 50-200ms for 1000 documents

### Memory Usage
- **Embedding Dimension**: 1536 (Groq default)
- **Per Document**: ~6KB (1536 floats × 4 bytes)
- **Example**: 10,000 documents ≈ 60MB embeddings

### Scalability Paths
1. **Small Scale** (< 1000 docs): Current SQLite setup
2. **Medium Scale** (1K-100K): Add FAISS or Milvus indexing
3. **Large Scale** (> 100K): Cloud vector DB (Pinecone, Weaviate)

## Security Architecture

- **Secrets Management**: Environment variables, no hardcoded keys
- **CORS**: Configurable origin whitelisting
- **Input Validation**: Pydantic models on all endpoints
- **Error Handling**: No sensitive information in error messages
- **Logging**: Sensitive data not logged

## Monitoring & Observability

- **Health Checks**: `/api/health/` endpoint
- **Logging**: Structured logging to file and console
- **Metrics Ready**: Infrastructure for adding Prometheus metrics
- **Request Logging**: Middleware logs all requests with timing

## Deployment Patterns

### Local Development
```bash
uvicorn datamind.main:app --reload
```

### Production (Docker)
```bash
docker run -p 8080:8080 datamind:latest
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: datamind
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: datamind
        image: datamind:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /api/health/live
            port: 8080
        readinessProbe:
          httpGet:
            path: /api/health/ready
            port: 8080
```

## Future Enhancements

1. **Vector Database Integration**: FAISS/Milvus for large-scale search
2. **Async Document Processing**: Celery/RQ for background jobs
3. **Advanced Chunking**: Intelligent document splitting
4. **Multi-tenancy**: Support for multiple users/organizations
5. **Streaming API**: Server-sent events for real-time responses
6. **Caching Layer**: Redis for query caching
7. **Fine-tuning**: Custom embedding models
8. **GraphQL API**: Alternative to REST for flexible queries
