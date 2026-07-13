# Backend RAG (FastAPI + LangChain/DeepSeek + ChromaDB embebido). Build context = repo root.
FROM python:3.12-slim

WORKDIR /app

# git: para scripts/fetch_repos.py (descarga del corpus). Sin torch → no hace falta compilador.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY database/ ./database/
COPY scripts/ ./scripts/

# app.*  se resuelve vía /app/backend ; database.* vía /app
ENV PYTHONPATH=/app/backend:/app
# El cerebro (ChromaDB) se HORNEA dentro de la imagen: no necesita volumen en Railway.
ENV CHROMA_PATH=/app/chroma_data

# Descarga la documentación oficial y genera los embeddings en tiempo de BUILD,
# dejando el corpus incluido en la imagen. Así el backend arranca ya con conocimiento.
RUN python scripts/fetch_repos.py && python -m app.ingest

ENV PORT=8001
# Railway inyecta $PORT en tiempo de ejecución.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
