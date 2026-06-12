import logging
import os
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger("AgentForge.Memory")

class MemoryService:
    def __init__(self):
        self.client = None
        self.collection = None
        self.enabled = False
        self._initialize_chroma()

    def _initialize_chroma(self):
        """Connect to local ChromaDB server or create persistent local folder."""
        try:
            import chromadb
            os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
            self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
            # Fetch or establish memory collection
            self.collection = self.client.get_or_create_collection(
                name="agentforge_memory"
            )
            self.enabled = True
            logger.info("ChromaDB vector memory initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to load ChromaDB. Semantic memory disabled: {e}")
            self.enabled = False

    async def index_message(
        self,
        conversation_id: str,
        message_id: str,
        sender_type: str,
        content: str
    ):
        """Index a chat completion message in local vector memory."""
        if not self.enabled or not self.collection:
            return
            
        try:
            # Add snippet to ChromaDB collection
            self.collection.add(
                documents=[content],
                metadatas=[{"conversation_id": conversation_id, "sender_type": sender_type}],
                ids=[message_id]
            )
            logger.info(f"Indexed message '{message_id}' in conversation '{conversation_id}'")
        except Exception as e:
            logger.error(f"Error vectorizing message in ChromaDB: {e}")

    async def search_memory(
        self,
        conversation_id: str,
        query: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve historically similar context chunks."""
        if not self.enabled or not self.collection or not query.strip():
            return []
            
        try:
            # Query collection with filter by conversation_id
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where={"conversation_id": conversation_id}
            )
            
            memories = []
            if results and "documents" in results and results["documents"]:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0] if "metadatas" in results else []
                
                for idx, doc in enumerate(documents):
                    meta = metadatas[idx] if idx < len(metadatas) else {}
                    memories.append({
                        "content": doc,
                        "sender_type": meta.get("sender_type", "unknown")
                    })
            return memories
        except Exception as e:
            logger.error(f"Error querying ChromaDB vector space: {e}")
            return []

    async def get_context_injection(self, conversation_id: str, query: str, limit: int = 3) -> str:
        """Construct context injection prompt segment from semantic memories."""
        memories = await self.search_memory(conversation_id, query, limit)
        if not memories:
            return ""

        context_prompt = "\n[Historical System Context - Semantic Matches from Conversation memory]:\n"
        for m in memories:
            role_name = "User" if m["sender_type"] == "user" else "Assistant"
            context_prompt += f"* {role_name} said: \"{m['content']}\"\n"
        context_prompt += "\n"
        return context_prompt

memory_service = MemoryService()
