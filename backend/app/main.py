import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from app.llm_chain import generate_answer

app = FastAPI(title="TeleAgent API", version="1.0.0")

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
