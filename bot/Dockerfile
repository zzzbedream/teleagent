# Bot de Discord (worker de larga duración). Build context = repo root.
FROM python:3.12-slim

WORKDIR /app

COPY bot/requirements.txt ./bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt

COPY bot/ ./bot/
COPY database/ ./database/

ENV PYTHONPATH=/app

CMD ["python", "bot/bot.py"]
