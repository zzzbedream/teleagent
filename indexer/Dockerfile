# Indexer on-chain (worker WSS de larga duración). Build context = repo root.
FROM python:3.12-slim

WORKDIR /app

COPY indexer/requirements.txt ./indexer/requirements.txt
RUN pip install --no-cache-dir -r indexer/requirements.txt

COPY indexer/ ./indexer/
COPY database/ ./database/

ENV PYTHONPATH=/app

CMD ["python", "indexer/indexer.py"]
