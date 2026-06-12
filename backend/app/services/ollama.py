import json
import logging
import httpx
from typing import AsyncGenerator, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger("AgentForge.Ollama")

class OllamaService:
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(60.0, connect=5.0)

    async def is_healthy(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """List models installed locally on Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("models", [])
                return []
        except Exception as e:
            logger.error(f"Error fetching models from Ollama: {e}")
            return []

    async def pull_model_stream(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream progress of downloading a model from Ollama library."""
        url = f"{self.base_url}/api/pull"
        payload = {"name": model_name, "stream": True}
        
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        yield {"status": "error", "message": f"Ollama returned status {response.status_code}"}
                        return
                    
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                yield json.loads(line)
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            yield {"status": "error", "message": str(e)}

    async def chat_completion_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream real-time tokens from Ollama chat completion API."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if options:
            payload["options"] = options

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        yield {"type": "error", "content": f"Ollama HTTP error {response.status_code}"}
                        return
                    
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                # Ollama streams back chunks containing:
                                # {"model": "...", "created_at": "...", "message": {"role": "assistant", "content": "..."}}
                                if "message" in chunk and "content" in chunk["message"]:
                                    yield {
                                        "type": "token",
                                        "content": chunk["message"]["content"],
                                        "done": chunk.get("done", False)
                                    }
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            logger.error(f"Error streaming chat completion from Ollama: {e}")
            yield {"type": "error", "content": f"Connection to Ollama failed: {str(e)}"}

ollama_service = OllamaService()
