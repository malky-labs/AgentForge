from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.schemas import User
from app.services.ollama import ollama_service
from app.services.memory_service import memory_service

router = APIRouter()

@router.get("", status_code=status.HTTP_200_OK)
async def check_health(session: Session = Depends(get_session)):
    """Deep health inspection of the database, memory, and LLM servers."""
    db_healthy = False
    try:
        # Check database execution query
        session.exec(select(1)).first()
        db_healthy = True
    except Exception:
        db_healthy = False

    ollama_healthy = await ollama_service.is_healthy()
    chroma_healthy = memory_service.enabled

    health_status = "healthy" if db_healthy else "unhealthy"
    
    response_payload = {
        "status": health_status,
        "components": {
            "database": "online" if db_healthy else "offline",
            "ollama_inference": "online" if ollama_healthy else "offline",
            "chromadb_vector_memory": "active" if chroma_healthy else "disabled"
        }
    }
    
    if not db_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response_payload
        )
        
    return response_payload
