# Backend RAG (FastAPI + LangChain/DeepSeek + ChromaDB). Build context = repo root.
FROM python:3.12-slim

WORKDIR /app

# git: para scripts/fetch_repos.py (corpus). build-essential: wheels que compilan.
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY database/ ./database/
COPY scripts/ ./scripts/

# app.*  se resuelve vía /app/backend ; database.* vía /app
ENV PYTHONPATH=/app/backend:/app
ENV PORT=8001

# Railway inyecta $PORT en tiempo de ejecución.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
