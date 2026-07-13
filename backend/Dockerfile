# Backend RAG (FastAPI + LangChain/DeepSeek + ChromaDB embebido). Build context = repo root.
FROM python:3.12-slim

WORKDIR /app

# git: para scripts/fetch_repos.py (descarga del corpus).
# libgomp1: requerido por onnxruntime (fastembed); sin él, el import crashea en imágenes slim.
RUN apt-get update && apt-get install -y --no-install-recommends git libgomp1 \
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
# Modelo de embeddings cacheado DENTRO de la imagen (si no, iría a /tmp y en runtime
# podría re-descargarse o no estar disponible).
ENV FASTEMBED_CACHE_PATH=/app/fastembed_cache

# 1) Descarga la documentación oficial  2) genera los embeddings (cerebro)
# 3) VERIFICA que el cerebro no quedó vacío (rompe el build si documents == 0)
# 4) borra los docs crudos (ya viven como embeddings; adelgaza la imagen)
RUN python scripts/fetch_repos.py \
    && python -m app.ingest \
    && python -c "import chromadb,os; n=chromadb.PersistentClient(path=os.environ['CHROMA_PATH']).get_collection('avalanche9000_core').count(); print(f'== CEREBRO HORNEADO: {n} documentos =='); raise SystemExit(0 if n>0 else 'ERROR: cerebro vacio, abortando build')" \
    && rm -rf /app/docs

ENV PORT=8001
# Railway inyecta $PORT en tiempo de ejecución.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
