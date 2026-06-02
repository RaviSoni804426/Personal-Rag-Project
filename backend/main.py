import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config.config import settings
from backend.database.connection import engine, Base
from backend.api.router import router as api_router

# Initialize database schemas
try:
    print("Auto-running relational database table migrations...")
    Base.metadata.create_all(bind=engine)
    print("Database tables synchronized.")
except Exception as e:
    print(f"Error during schema synchronization: {e}")

# Create application
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Knowledge Intelligence and Advanced Semantic Retrieval Platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production to match exact client domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# Mount Routers
app.include_router(api_router)

# Mount frontend static files if they are compiled
static_dir = "./backend/static"
if os.path.exists(static_dir):
    print("Serving Next.js frontend UI from static files bundle...")
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/")
    def read_root():
        return {
            "status": "online",
            "service": settings.APP_NAME,
            "features": [
                "Ingestion loaders (PDF, Word, CSV, Excel, MD, HTML)",
                "Advanced splitting (Recursive, Semantic, Parent-Child)",
                "Dual hybrid retrieve (Vector Cosine + BM25 keyword matching)",
                "Deep Cross-Encoder reranking",
                "Full RAG LLM response synthesis",
                "Auto evaluation analytics"
            ]
        }


if __name__ == "__main__":
    import uvicorn
    # Use standard host configuration for production/docker containers
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
