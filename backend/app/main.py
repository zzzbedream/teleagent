import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from app.llm_chain import generate_answer

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Orígenes permitidos para la landing (demo en vivo). Coma-separados; "*" por defecto.
# Sin credenciales, así que el wildcard es seguro para un endpoint de solo lectura.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas (idempotente) para que bot e indexer tengan el esquema listo.
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            from database.models import init_db
            await init_db(database_url)
            logging.info("Database schema ensured.")
        except Exception as e:
            logging.warning(f"Could not initialize DB schema at startup: {e}")
    yield


app = FastAPI(title="TeleAgent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    prompt: str


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        result = await generate_answer(request.prompt)
        return result
    except RuntimeError as re:
        logging.error(f"RuntimeError in /query: {re}")
        raise HTTPException(status_code=503, detail="Vector database (ChromaDB) is unavailable or connection failed.")
    except Exception as e:
        logging.error(f"Unexpected error in /query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while processing the query.")
