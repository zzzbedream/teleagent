import os
import re
import logging
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
import chromadb
from langchain_community.vectorstores import Chroma

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def hybrid_split_documents(docs):
    """
    Hybrid chunking: 
    - Text/Markdown: standard chunking
    - Code (Solidity/Go/TS): regex splitting on closing braces to avoid breaking functions.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    
    split_docs = []
    for doc in docs:
        ext = os.path.splitext(doc.metadata.get("source", ""))[1].lower()
        if ext in ['.sol', '.go', '.ts', '.js', '.py']:
            # Regex to split on closing brace followed by newline, keeping the brace.
            chunks = re.split(r'(?<=\})\s*\n+', doc.page_content)
            
            for chunk in chunks:
                if chunk.strip():
                    doc_copy = doc.copy()
                    doc_copy.page_content = chunk.strip()
                    # Ensure it's not too huge
                    if len(doc_copy.page_content) > 2000:
                        split_docs.extend(text_splitter.split_documents([doc_copy]))
                    else:
                        split_docs.append(doc_copy)
        else:
            # Fallback to standard for md/txt
            split_docs.extend(text_splitter.split_documents([doc]))
            
    return split_docs

def main():
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs"))
    if not os.path.exists(docs_dir):
        logging.error(f"Docs directory {docs_dir} does not exist.")
        return

    logging.info("Loading documents...")
    # Load all files with specific extensions
    extensions = ['**/*.md', '**/*.mdx', '**/*.txt', '**/*.sol', '**/*.go', '**/*.ts']
    all_docs = []
    for ext in extensions:
        loader = DirectoryLoader(docs_dir, glob=ext, loader_cls=TextLoader, silent_errors=True)
        docs = loader.load()
        all_docs.extend(docs)
    
    logging.info(f"Loaded {len(all_docs)} documents.")
    
    logging.info("Applying hybrid chunking...")
    chunked_docs = hybrid_split_documents(all_docs)
    logging.info(f"Generated {len(chunked_docs)} chunks.")

    logging.info("Initializing FastEmbed (ONNX) embeddings...")
    embeddings = FastEmbedEmbeddings()

    chroma_path = os.getenv("CHROMA_PATH", "./chroma_data")
    logging.info(f"Opening embedded ChromaDB at {chroma_path}...")
    client = chromadb.PersistentClient(path=chroma_path)

    # Ensure collection exists and is clean (idempotency)
    collection_name = "avalanche9000_core"
    try:
        client.delete_collection(collection_name)
        logging.info(f"Deleted existing collection: {collection_name}")
    except Exception:
        pass
    
    logging.info("Ingesting into ChromaDB...")
    vectorstore = Chroma.from_documents(
        documents=chunked_docs,
        embedding=embeddings,
        collection_name=collection_name,
        client=client
    )
    
    logging.info("Ingestion complete!")

if __name__ == "__main__":
    main()
