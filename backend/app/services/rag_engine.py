import io
import re
import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from app.core.config import settings
from app.services.memory_service import memory_service

logger = logging.getLogger("AgentForge.RAG")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract clean text lines from PDF byte streams using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- Page {page_idx + 1} ---\n{page_text}\n"
        return text
    except ImportError:
        logger.warning("pypdf is not installed. Falling back to plain text decode.")
        return file_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Error parsing PDF document bytes: {e}")
        return ""

def extract_text_from_markdown(content: str) -> str:
    """Sanitize and clean Markdown headers and layouts."""
    # Strip HTML tags if any exist
    text = re.sub(r'<[^>]*>', '', content)
    # Return formatted content
    return text

def extract_text_from_web(html_content: str) -> str:
    """Extract readable text block contents from website HTML code."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        # Strip script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        # Get text
        text = soup.get_text()
        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        return "\n".join(chunk for chunk in chunks if chunk)
    except Exception as e:
        logger.warning(f"BeautifulSoup parsing failed: {e}. Falling back to regex.")
        # Regex fallback to strip tags
        return re.sub(r'<[^>]*>', '', html_content)

def split_text_into_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """Segment a document string into overlapping character-level windows."""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - chunk_overlap
        
    return chunks

class RAGEngine:
    def __init__(self):
        self.embed_model = "nomic-embed-text"

    async def get_embedding(self, text: str) -> List[float]:
        """Fetch vector embeddings array for a string from local Ollama API."""
        url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
        payload = {"model": self.embed_model, "prompt": text}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=20.0)
                if response.status_code == 200:
                    return response.json().get("embedding", [])
            except Exception as err:
                logger.warning(f"Ollama embeddings endpoint error: {err}. Trying alternative API path.")
            
            # Fallback API path /api/embed
            url_alt = f"{settings.OLLAMA_BASE_URL}/api/embed"
            payload_alt = {"model": self.embed_model, "input": text}
            try:
                response = await client.post(url_alt, json=payload_alt, timeout=20.0)
                if response.status_code == 200:
                    embeddings = response.json().get("embeddings", [])
                    if embeddings:
                        return embeddings[0]
            except Exception as err:
                logger.error(f"Fallback embed API failed: {err}")
                
        # Return dummy 384-sized vector representation if Ollama is unreachable
        return [0.0] * 384

    def get_collection_index(self, collection_id: str):
        """Fetch or create segmented ChromaDB collection space."""
        import chromadb
        if not memory_service.client:
            os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
            memory_service.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        
        clean_uuid = str(collection_id).replace("-", "_")
        col_name = f"collection_{clean_uuid}"
        return memory_service.client.get_or_create_collection(name=col_name)

    async def ingest_document(
        self,
        collection_id: str,
        document_id: str,
        name: str,
        file_type: str,
        raw_bytes: bytes
    ):
        """Parse, chunk, embed, and index a document in ChromaDB."""
        # 1. Parse text based on document type
        text_content = ""
        if file_type == "pdf":
            text_content = extract_text_from_pdf(raw_bytes)
        elif file_type == "md":
            text_content = extract_text_from_markdown(raw_bytes.decode("utf-8", errors="ignore"))
        elif file_type == "web":
            text_content = extract_text_from_web(raw_bytes.decode("utf-8", errors="ignore"))
        else:
            text_content = raw_bytes.decode("utf-8", errors="ignore")

        if not text_content.strip():
            raise ValueError("Parsed document yielded empty text content.")

        # 2. Chunk text
        chunks = split_text_into_chunks(text_content, chunk_size=600, chunk_overlap=80)
        
        # 3. Add to ChromaDB index
        collection = self.get_collection_index(collection_id)
        
        # Generate embeddings
        ids = []
        embeddings = []
        metadatas = []
        documents = []
        
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{idx}"
            vector = await self.get_embedding(chunk)
            
            ids.append(chunk_id)
            embeddings.append(vector)
            documents.append(chunk)
            metadatas.append({
                "document_id": str(document_id),
                "document_name": name,
                "chunk_index": idx
            })
            
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        logger.info(f"Ingested document {document_id} into collection {collection_id} ({len(chunks)} chunks)")

    async def query_knowledge(
        self,
        collection_id: str,
        query: str,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """Query vector database for similar context blocks."""
        collection = self.get_collection_index(collection_id)
        query_vector = await self.get_embedding(query)
        
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=limit
        )
        
        retrieved = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else []
            distances = results["distances"][0] if "distances" in results else []
            
            for idx, doc in enumerate(docs):
                meta = metas[idx] if idx < len(metas) else {}
                dist = distances[idx] if idx < len(distances) else 0.0
                retrieved.append({
                    "content": doc,
                    "document_name": meta.get("document_name", "Unknown"),
                    "document_id": meta.get("document_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "score": float(dist)
                })
        return retrieved

    async def build_citations_context(self, collection_id: str, query: str, limit: int = 3) -> str:
        """Construct prompt context block containing retrieved references."""
        matches = await self.query_knowledge(collection_id, query, limit)
        if not matches:
            return ""
            
        context = "\n[Retrieved Context from Knowledge Base Collections]:\n"
        for idx, m in enumerate(matches):
            context += f"Reference [{idx + 1}] (Document: {m['document_name']}):\n"
            context += f"\"\"\"\n{m['content']}\n\"\"\"\n\n"
            
        context += "Instructions: Answer the user using the reference brackets above to cite your answers (e.g. 'like standard actions [1].').\n"
        return context

rag_engine = RAGEngine()
