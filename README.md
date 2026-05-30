# DataMind - Intelligent Document Intelligence Platform

---
title: DataMind
emoji: "🧠"
colorFrom: "blue"
colorTo: "cyan"
sdk: docker
sdk_version: "1.0"
python_version: "3.11"
app_file: datamind.main:app
pinned: false
---

> Enterprise-grade semantic search and document analysis platform powered by AI embeddings and large language models.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Overview

DataMind is a production-ready platform designed to solve enterprise document intelligence challenges. It enables organizations to:

- **Semantic Search**: Find relevant documents using natural language queries, not just keywords
- **Intelligent Q&A**: Get accurate answers from your document library using AI
- **Document Classification**: Automatically categorize and tag documents
- **Analytics & Insights**: Understand your document repository with advanced analytics
- **Scalable Architecture**: Handle large document collections with optimized vector search

## ✨ Key Features

### 🔍 Semantic Search
- Advanced natural language understanding using Groq embeddings
- Similarity-based document retrieval with configurable thresholds
- Real-time search with millisecond response times
- Support for multi-document context retrieval

### 💬 AI-Powered Chat
- Conversational interface for document queries
- Context-aware responses using retrieved documents
- Optional LLM integration (OpenAI GPT-4) for intelligent synthesis
- Conversation history tracking

### 📄 Document Management
- Support for multiple formats: PDF, DOCX, TXT, MD, JSON, CSV
- Automatic text extraction and preprocessing
- Batch document ingestion for bulk operations
- Document metadata and tagging system

### 📊 Analytics Dashboard
- Real-time statistics on document collection
- Search performance metrics
- Document type distribution
- Storage utilization insights

### 🔒 Enterprise Ready
- Built with FastAPI for high performance
- Comprehensive error handling and logging
- Health checks and readiness probes
- Docker containerization for easy deployment
- CORS support for frontend integration

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Groq API Key (get one free at [console.groq.com](https://console.groq.com))
- OpenAI API Key (optional, for LLM features)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/datamind.git
cd datamind
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your API keys:
# - GROQ_API_KEY (required)
# - OPENAI_API_KEY (optional)
```

5. **Run the application**
```bash
uvicorn datamind.main:app --host 0.0.0.0 --port 8080
```

6. **Access the UI**
Open your browser and navigate to `http://localhost:8080`

## 📖 Usage

### Web UI
The intuitive web interface provides:
- **Chat Tab**: Ask questions about your documents
- **Search Tab**: Perform semantic searches
- **Documents Tab**: Manage your document library
- **Analytics Tab**: View statistics and insights

### API Endpoints

#### Upload Documents
```bash
curl -X POST http://localhost:8080/api/documents/upload \
  -F "files=@document.pdf"
```

#### Semantic Search
```bash
curl -X POST http://localhost:8080/api/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings?",
    "top_k": 5
  }'
```

#### Ask Questions
```bash
curl -X POST http://localhost:8080/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Summarize the key points",
    "top_k": 5
  }'
```

#### Get Statistics
```bash
curl http://localhost:8080/api/documents/stats
```

#### Health Check
```bash
curl http://localhost:8080/api/health/
```

## 🐳 Docker Deployment

### Build Docker Image
```bash
docker build -t datamind:latest .
```

### Run with Docker
```bash
docker run -p 8080:8080 \
  -e GROQ_API_KEY="your_key" \
  -e OPENAI_API_KEY="your_key" \
  datamind:latest
```

## ☁️ Hugging Face Deployment

Deploy to Hugging Face Spaces in minutes:

1. Create new Space (Docker runtime)
2. Push this repository to the Space
3. Add `GROQ_API_KEY` and optional `OPENAI_API_KEY` to Space secrets
4. Space will auto-deploy

See [HUGGING_FACE_DEPLOY.md](HUGGING_FACE_DEPLOY.md) for detailed instructions.

## 🔐 Security Considerations

- Never commit `.env` file with secrets
- Use environment variables for all sensitive data
- Enable HTTPS in production
- Implement rate limiting
- Use authentication for API endpoints
- Keep dependencies updated

## 📚 API Documentation

Once running, access interactive API docs:
- **Swagger UI**: `http://localhost:8080/api/docs`
- **ReDoc**: `http://localhost:8080/api/redoc`

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋 Support

For issues, questions, and discussions, please visit the [GitHub repository](https://github.com/yourusername/datamind).

---

Built with ❤️ using FastAPI, Groq, and OpenAI
