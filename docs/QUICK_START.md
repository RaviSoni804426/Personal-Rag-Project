# DataMind - Quick Start Guide

## 5-Minute Setup

### 1. Get Your API Keys

**Groq API Key (Required):**
- Go to [console.groq.com](https://console.groq.com)
- Sign up or login
- Create new API key
- Copy the key

**OpenAI API Key (Optional):**
- Go to [platform.openai.com](https://platform.openai.com)
- Sign up or login  
- Create new API key
- Copy the key

### 2. Clone & Setup

```bash
# Navigate to your project
cd datamind

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 3. Configure Environment

Edit `.env`:
```
GROQ_API_KEY=gsk_YOUR_KEY_HERE
OPENAI_API_KEY=sk_YOUR_KEY_HERE  # Optional
```

### 4. Run Application

```bash
uvicorn datamind.main:app --reload
```

**Access:**
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **API ReDoc**: http://localhost:8000/api/redoc

---

## Using the Web UI

### Chat Tab
1. Upload documents using the upload area
2. Type your question in the text box
3. Click "Send" or press Ctrl+Enter
4. Get answer + retrieved context

### Search Tab  
1. Enter search query
2. Adjust "Results per query" (1-20)
3. Click "Search"
4. View results with similarity scores

### Documents Tab
1. View all uploaded documents
2. See document size, type, content preview
3. Delete individual documents

### Analytics Tab
1. View total documents count
2. See total character count
3. Check average document size
4. See document types

---

## Common Tasks

### Upload Documents
```bash
# Single file
curl -X POST http://localhost:8000/api/documents/upload \
  -F "files=@document.pdf"

# Multiple files
curl -X POST http://localhost:8000/api/documents/upload \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.txt"
```

### Search for Documents
```bash
curl -X POST http://localhost:8000/api/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings?",
    "top_k": 5,
    "similarity_threshold": 0.0
  }'
```

### Ask a Question
```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Summarize the key points",
    "top_k": 5
  }'
```

### Get Statistics
```bash
curl http://localhost:8000/api/documents/stats
```

### Check Health
```bash
curl http://localhost:8000/api/health/
```

---

## Troubleshooting

### "GROQ_API_KEY not configured"
- Ensure `.env` file exists in project root
- Check that `GROQ_API_KEY` is set correctly
- Restart the application

### Search is slow
- This is normal for first query (cold start)
- Subsequent queries are faster
- Performance improves with proper database indexing

### Upload fails with 400 error
- Check file format (PDF, DOCX, TXT, MD supported)
- Ensure file is not corrupted
- File should contain readable text

### "Connection refused" error
- Make sure app is running: `uvicorn datamind.main:app --reload`
- Check port 8000 is not in use: `lsof -i :8000`
- Try different port: `uvicorn datamind.main:app --port 8001`

### App crashes on startup
- Check `.env` file is valid
- Verify `GROQ_API_KEY` is correct
- Check `requirements.txt` dependencies installed: `pip install -r requirements.txt`
- Check Python version 3.11+: `python --version`

---

## Configuration Options

### Search
```
DEFAULT_TOP_K=5           # Results per search by default
MAX_TOP_K=20              # Maximum results allowed
SIMILARITY_THRESHOLD=0.0  # Minimum similarity score (0-1)
```

### Performance
```
BATCH_SIZE=10             # Documents per batch during ingestion
REQUEST_TIMEOUT=30        # API timeout in seconds
```

### Logging
```
LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
LOG_FILE=./logs/datamind.log
```

### Database
```
DB_PATH=./data/datamind.db
```

---

## Docker Usage

### Build Image
```bash
docker build -t datamind:latest .
```

### Run Container
```bash
docker run -p 8080:8080 \
  -e GROQ_API_KEY="your_key" \
  -e OPENAI_API_KEY="your_key" \
  datamind:latest
```

### Access
- Open http://localhost:8080

---

## Hugging Face Spaces

### Deploy in 5 Steps
1. Create Space at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Choose Docker runtime
3. Clone Space repo locally
4. Copy DataMind files to Space
5. Push to HF: `git push`

### Add Secrets
1. Space settings → Secrets
2. Add `GROQ_API_KEY`
3. Add `OPENAI_API_KEY` (optional)

See `HUGGING_FACE_DEPLOY.md` for detailed instructions

---

## API Reference

### Endpoints

#### Documents API

**Upload Document**
```
POST /api/documents/upload
Content-Type: multipart/form-data
Files: files, files, ...
Response: DocumentInfo (first file)
```

**Search Documents**
```
POST /api/documents/search
{
  "query": "string",
  "top_k": 5,
  "similarity_threshold": 0.0
}
Response: SearchResponse
```

**Get All Documents**
```
GET /api/documents/
Response: List[DocumentInfo]
```

**Get Single Document**
```
GET /api/documents/{doc_id}
Response: DocumentInfo
```

**Delete Document**
```
DELETE /api/documents/{doc_id}
Response: {"message": "Document deleted successfully"}
```

**Get Statistics**
```
GET /api/documents/stats
Response: DocumentStats
```

#### Chat API

**Send Message**
```
POST /api/chat/
{
  "message": "string",
  "top_k": 5,
  "conversation_id": "string" (optional),
  "system_prompt": "string" (optional)
}
Response: ConversationResponse
```

#### Health API

**Health Check**
```
GET /api/health/
Response: HealthResponse
```

**Readiness Probe**
```
GET /api/health/ready
Response: {"ready": boolean, "message": "string"}
```

**Liveness Probe**
```
GET /api/health/live
Response: {"alive": boolean}
```

---

## Python SDK Example

```python
from datamind.storage import VectorStore
from datamind.services import DocumentService
from datamind.config import settings

# Initialize
store = VectorStore(settings.DB_PATH)
service = DocumentService(store)

# Ingest document
doc_id = service.ingest_document(
    filename="report.txt",
    content="Long document content here...",
    doc_type="txt",
    tags=["annual", "report"]
)

# Search
results = service.search(query="Key findings", top_k=5)
for result in results:
    print(f"{result.filename}: {result.similarity_score}")

# Q&A
answer_data = service.get_answer(query="What are key metrics?")
print(f"Answer: {answer_data['answer']}")
print(f"Sources: {answer_data['retrieved']}")

# Get stats
stats = service.get_stats()
print(f"Total documents: {stats['total_documents']}")
```

---

## Performance Tips

1. **Batch uploads**: Upload multiple documents at once
2. **Proper queries**: Be specific, natural language works best
3. **Manage size**: Delete old documents to keep database lean
4. **Monitor logs**: Check `logs/datamind.log` for issues

---

## What's Next?

- ✅ Documents uploaded
- ✅ Semantic search working
- ✅ Q&A enabled
- ⬜ Deploy to production
- ⬜ Add more documents
- ⬜ Integrate with your app

---

## Need Help?

- **Docs**: See `docs/` folder
- **API Docs**: http://localhost:8000/api/docs
- **Issues**: Check application logs at `logs/datamind.log`
- **GitHub**: Open issue on repository

---

**Start using DataMind now!** 🚀
