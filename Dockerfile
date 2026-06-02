# ========================================================
# Enterprise Knowledge Intelligence Platform Docker Setup
# ========================================================

# --- Stage 1: Build Frontend Next.js Assets ---
FROM node:18-slim AS frontend-builder

WORKDIR /frontend

# Copy package descriptors first to maximize caching
COPY frontend/package.json ./
RUN npm install

# Copy source files and compile statically
COPY frontend/ ./
RUN npm run build


# --- Stage 2: Initialize Backend Dependencies ---
FROM python:3.11-slim AS backend-builder

WORKDIR /backend
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt


# --- Stage 3: Final Production Runner ---
FROM python:3.11-slim AS runner

WORKDIR /app

# Create secure non-privileged system execution user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copy Python packages from builder stage
COPY --from=backend-builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

# Copy backend files
COPY --chown=appuser:appgroup backend/ ./backend/

# Copy built frontend assets into FastAPI mount point
COPY --from=frontend-builder --chown=appuser:appgroup /frontend/out/ ./backend/static/

# Copy root configurations
COPY --chown=appuser:appgroup README.md .
COPY --chown=appuser:appgroup .env.example .

# Create persistent storage directories
RUN mkdir -p /app/data /app/data/chroma_db /app/data/uploads && \
    chown -R appuser:appgroup /app/data

USER appuser

# Expose single serving port
EXPOSE 7860

ENV HOST=0.0.0.0
ENV PORT=7860
ENV DATABASE_URL=sqlite:////app/data/rag_platform.db
ENV CHROMA_PERSIST_DIR=/app/data/chroma_db

# Run FastAPI app
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
