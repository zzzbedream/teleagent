import os
import logging
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import chromadb

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
# ChromaDB embebido (persistente). En Railway el volumen se monta en /data → CHROMA_PATH=/data/chroma.
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_data")
COLLECTION_NAME = "avalanche9000_core"

# Cacheados a nivel módulo: crear el cliente/embeddings/cadena es costoso.
_chain = None
_chroma_client = None


def _get_chroma_client():
    """Cliente único de ChromaDB embebido (evita abrir varios al mismo path)."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


def get_document_count() -> int | None:
    """Cuántos documentos hay indexados en ChromaDB.

    Sirve para verificar de un vistazo que el "cerebro" está cargado.
    Devuelve el conteo, 0 si la colección aún no existe, o None si Chroma no responde.
    """
    try:
        client = _get_chroma_client()
        try:
            collection = client.get_collection(COLLECTION_NAME)
        except Exception:
            return 0  # Chroma vivo pero el corpus todavía no se ha sembrado.
        return collection.count()
    except Exception as e:
        logging.warning(f"No se pudo consultar el conteo de ChromaDB: {e}")
        return None

def get_retriever():
    try:
        # MISMO modelo multilingüe que en ingest.py (si difieren, la búsqueda se rompe).
        embeddings = FastEmbedEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        vectorstore = Chroma(
            client=_get_chroma_client(),
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings
        )
        return vectorstore.as_retriever(search_kwargs={"k": 8})
    except Exception as e:
        logging.error(f"Error connecting to ChromaDB: {e}")
        raise RuntimeError("Vector database is unavailable.")

def build_chain():
    api_key = os.getenv("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY)
    if not api_key:
        logging.warning("DEEPSEEK_API_KEY is not set. The LLM call will fail.")

    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0,
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
    
    system_prompt = """Eres TeleAgent, un asistente experto en Avalanche9000 para desarrolladores.

REGLAS:
1. Responde basándote en el CONTEXTO proporcionado. Puedes sintetizar y combinar varios fragmentos del contexto para armar una respuesta útil y completa.
2. Si el contexto cubre la pregunta solo parcialmente, responde con lo que SÍ está en el contexto y aclara brevemente qué parte no está cubierta.
3. Dato verificado que puedes usar siempre: la actualización Etna (ACP-77) eliminó el requisito de 2,000 AVAX para validar Subnets; ahora son L1s soberanas con un modelo de tarifa continua de pago por uso.
4. SOLO si el contexto no tiene NINGUNA relación con la pregunta, responde textualmente: "No tengo suficiente información en la documentación oficial de Avalanche9000 para responder esto de forma segura."
5. NUNCA inventes comandos, direcciones, cifras ni APIs que no aparezcan en el contexto o en estas reglas.
6. Responde en el mismo idioma de la pregunta.

Contexto:
{context}

Pregunta del usuario:
{input}
"""
    
    prompt = PromptTemplate.from_template(system_prompt)
    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = get_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)

    return retrieval_chain

def get_chain():
    global _chain
    if _chain is None:
        _chain = build_chain()
    return _chain

async def generate_answer(user_query: str) -> dict:
    try:
        chain = get_chain()
        response = await chain.ainvoke({"input": user_query})
        
        # Format sources
        sources = []
        if "context" in response:
            for doc in response["context"]:
                source = doc.metadata.get("source", "Unknown")
                if source not in sources:
                    sources.append(source)
                    
        return {
            "answer": response.get("answer", ""),
            "sources": sources
        }
    except RuntimeError as re:
        raise re
    except Exception as e:
        logging.error(f"Error generating answer: {e}")
        raise e
