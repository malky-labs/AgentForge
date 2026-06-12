import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.services.ollama import ollama_service
from app.api.deps import get_current_user
from app.models.schemas import User

router = APIRouter()

@router.get("/models")
async def list_models(current_user: User = Depends(get_current_user)):
    """Fetch installed local models from Ollama."""
    models = await ollama_service.list_models()
    return {"models": models}

@router.post("/pull")
async def pull_model(
    model_name: str,
    current_user: User = Depends(get_current_user)
):
    """Initiate and stream a model download from Ollama registry."""
    if not await ollama_service.is_healthy():
        raise HTTPException(
            status_code=503,
            detail="Ollama service is currently unreachable. Make sure Ollama is running locally."
        )

    async def event_generator():
        async for progress in ollama_service.pull_model_stream(model_name):
            yield json.dumps(progress) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
