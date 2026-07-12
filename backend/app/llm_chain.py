import os
import logging
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import chromadb

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

# Cadena cacheada a nivel módulo: cargar embeddings y conectar a Chroma es costoso.
_chain = None

def get_retriever():
    try:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        vectorstore = Chroma(
            client=client,
            collection_name="avalanche9000_core",
            embedding_function=embeddings
        )
        return vectorstore.as_retriever(search_kwargs={"k": 5})
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
    
    system_prompt = """Eres TeleAgent, un asistente experto exclusivo de Avalanche9000.

REGLA CRÍTICA 1: Eres TeleAgent, un asistente experto exclusivo de Avalanche9000.
REGLA CRÍTICA 2: La actualización Etna eliminó el requisito de 2,000 AVAX. Ahora se usan L1s soberanas.
REGLA CRÍTICA 3: Responde ÚNICAMENTE usando el contexto proporcionado. Si la respuesta no está en el contexto, di textualmente: "No tengo suficiente información en la documentación oficial de Avalanche9000 para responder esto de forma segura." NO INVENTES CÓDIGO.

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
