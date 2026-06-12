import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.api.deps import get_current_user
from app.models.schemas import User, KnowledgeCollection, KnowledgeCollectionCreate, KnowledgeDocument
from app.services.rag_engine import rag_engine

logger = logging.getLogger("AgentForge.KnowledgeAPI")
router = APIRouter()

@router.post("/collections", response_model=KnowledgeCollection, status_code=status.HTTP_201_CREATED)
def create_collection(
    *,
    session: Session = Depends(get_session),
    collection_in: KnowledgeCollectionCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new knowledge collection grouping."""
    db_col = KnowledgeCollection(
        name=collection_in.name,
        description=collection_in.description,
        user_id=current_user.id
    )
    session.add(db_col)
    session.commit()
    session.refresh(db_col)
    return db_col

@router.get("/collections", response_model=List[KnowledgeCollection])
def list_collections(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all knowledge collections owned by the current user."""
    statement = select(KnowledgeCollection).where(KnowledgeCollection.user_id == current_user.id)
    return session.exec(statement).all()

@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    *,
    session: Session = Depends(get_session),
    collection_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Delete a knowledge collection and its database logs."""
    col = session.get(KnowledgeCollection, collection_id)
    if not col or col.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Knowledge collection not found.")
        
    # Delete associated documents
    statement = select(KnowledgeDocument).where(KnowledgeDocument.collection_id == collection_id)
    docs = session.exec(statement).all()
    for doc in docs:
        session.delete(doc)
        
    # Delete collection in ChromaDB
    try:
        import chromadb
        from app.services.memory_service import memory_service
        if memory_service.client:
            clean_uuid = str(collection_id).replace("-", "_")
            col_name = f"collection_{clean_uuid}"
            memory_service.client.delete_collection(name=col_name)
    except Exception as e:
        logger.warning(f"Could not delete collection from ChromaDB: {e}")

    session.delete(col)
    session.commit()
    return None

@router.post("/collections/{collection_id}/upload")
async def upload_document(
    collection_id: UUID,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Upload a PDF, Markdown, or text file to a knowledge collection."""
    col = session.get(KnowledgeCollection, collection_id)
    if not col or col.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Knowledge collection not found.")

    # Determine file extension/type
    filename = file.filename or "unknown"
    ext = filename.split(".")[-1].lower()
    file_type = "txt"
    if ext in ["pdf"]:
        file_type = "pdf"
    elif ext in ["md", "markdown"]:
        file_type = "md"
    elif ext in ["html", "htm"]:
        file_type = "web"

    # Read bytes
    content_bytes = await file.read()
    size = len(content_bytes)

    # Save initial database record
    db_doc = KnowledgeDocument(
        collection_id=collection_id,
        name=filename,
        file_type=file_type,
        size_bytes=size,
        status="processing"
    )
    session.add(db_doc)
    session.commit()
    session.refresh(db_doc)

    try:
        # Run parse chunk and embed indexing loop
        await rag_engine.ingest_document(
            collection_id=str(collection_id),
            document_id=str(db_doc.id),
            name=filename,
            file_type=file_type,
            raw_bytes=content_bytes
        )
        db_doc.status = "completed"
    except Exception as err:
        logger.exception(f"Document ingestion crashed for '{filename}':")
        db_doc.status = "failed"
        db_doc.error_message = str(err)
        
    session.add(db_doc)
    session.commit()
    session.refresh(db_doc)
    return db_doc

@router.get("/collections/{collection_id}/documents", response_model=List[KnowledgeDocument])
def list_documents(
    collection_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List all parsed documents inside a knowledge collection."""
    col = session.get(KnowledgeCollection, collection_id)
    if not col or col.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Knowledge collection not found.")
        
    statement = select(KnowledgeDocument).where(KnowledgeDocument.collection_id == collection_id)
    return session.exec(statement).all()

@router.post("/collections/{collection_id}/query")
async def query_collection(
    collection_id: UUID,
    query: str = Form(...),
    limit: int = Form(3),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Perform a manual similarity check against the collection index."""
    col = session.get(KnowledgeCollection, collection_id)
    if not col or col.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Knowledge collection not found.")
        
    results = await rag_engine.query_knowledge(
        collection_id=str(collection_id),
        query=query,
        limit=limit
    )
    return {"query": query, "results": results}
