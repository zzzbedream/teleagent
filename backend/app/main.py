import os
import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# IMPORTANTE: NO importamos app.llm_chain aquí. Eso cargaría langchain + chromadb + onnxruntime
# al arrancar (lento y pesado) y el healthcheck de Railway fallaría. Se importa de forma
# perezosa dentro de cada endpoint, así el arranque es instantáneo y /health responde al toque.

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Orígenes permitidos para la landing (demo en vivo). Coma-separados; "*" por defecto.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]


async def _ensure_db_schema():
    """Crea las tablas (idempotente). Corre en segundo plano para no bloquear el arranque."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return
    try:
        from database.models import init_db
        # Timeout: si la DB no responde, no dejamos una tarea colgada para siempre.
        await asyncio.wait_for(init_db(database_url), timeout=60)
        logging.info("Database schema ensured.")
    except Exception as e:
        logging.warning(f"Could not initialize DB schema at startup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # En segundo plano: el arranque termina de inmediato y el healthcheck pasa sin esperar a la DB.
    asyncio.create_task(_ensure_db_schema())
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


@app.get("/")
async def index():
    # Índice amigable: evita el confuso {"detail":"Not Found"} al abrir la URL base.
    return {
        "service": "TeleAgent API",
        "endpoints": {
            "health": "GET /health (vivo?)",
            "status": "GET /status (documentos del cerebro)",
            "query": "POST /query {prompt}",
        },
    }


@app.get("/health")
async def health_check():
    # Trivial y siempre 200: es lo que revisa el healthcheck de Railway. No carga nada pesado.
    return {"status": "ok"}


@app.get("/status")
async def status():
    # Reporta cuántos documentos tiene el cerebro (carga chromadb perezosamente).
    from app.llm_chain import get_document_count
    return {"status": "ok", "documents": get_document_count()}


@app.post("/query")
async def query_endpoint(request: QueryRequest):
    from app.llm_chain import generate_answer  # carga perezosa de la maquinaria RAG
    try:
        result = await generate_answer(request.prompt)
        return result
    except RuntimeError as re:
        logging.error(f"RuntimeError in /query: {re}")
        raise HTTPException(status_code=503, detail="Vector database (ChromaDB) is unavailable or connection failed.")
    except Exception as e:
        logging.error(f"Unexpected error in /query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while processing the query.")
