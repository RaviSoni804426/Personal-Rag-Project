# ==========================================
# DataMind Enterprise RAG Docker Configuration
# ==========================================

# --- Stage 1: Build & Dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system utilities needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to optimize Docker build caching layers
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# --- Stage 2: Final Run Image ---
FROM python:3.11-slim AS runner

WORKDIR /app

# Create a non-privileged system user and group for maximum security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copy installed python dependencies from build stage
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application source code
COPY --chown=appuser:appgroup datamind/ ./datamind/
COPY --chown=appuser:appgroup README.md .
COPY --chown=appuser:appgroup .env.example .

# Create writable data directories for SQLite db and file uploads
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appgroup /app/data /app/logs

# Switch container execution context to non-root user
USER appuser

# Configure runtime environments
ENV HOST=0.0.0.0
ENV PORT=8080
ENV DB_PATH=/app/data/datamind.db
ENV UPLOAD_DIR=/app/data/uploads
ENV LOG_FILE=/app/logs/datamind.log
ENV DEBUG=false

# Expose ports
EXPOSE 8080
EXPOSE 7860

# Run FastAPI app with uvicorn. sh -c evaluates ${PORT} dynamically at runtime (highly recommended for Hugging Face Spaces port 7860)
CMD ["sh", "-c", "uvicorn datamind.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2"]
