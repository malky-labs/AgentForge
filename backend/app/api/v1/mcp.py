from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.api.deps import get_current_user
from app.models.schemas import User, McpServer, McpServerCreate, Tool
from app.services.mcp_manager import mcp_manager

router = APIRouter()

@router.get("/servers", response_model=List[McpServer])
def list_servers(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List all registered MCP server configurations."""
    statement = select(McpServer)
    return session.exec(statement).all()

@router.post("/servers", response_model=McpServer, status_code=status.HTTP_201_CREATED)
def register_server(
    *,
    session: Session = Depends(get_session),
    server_in: McpServerCreate,
    current_user: User = Depends(get_current_user)
):
    """Register a new MCP server execution configuration."""
    # Ensure unique name
    stmt = select(McpServer).where(McpServer.name == server_in.name)
    existing = session.exec(stmt).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An MCP server with this name is already registered."
        )

    db_server = McpServer.model_validate(server_in)
    session.add(db_server)
    session.commit()
    session.refresh(db_server)
    return db_server

@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    *,
    session: Session = Depends(get_session),
    server_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Unregister and stop an MCP server subprocess."""
    server = session.get(McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server configuration not found.")
    
    # Terminate running process if any
    await mcp_manager.stop_server(server_id, session)
    
    # Delete associated tools
    stmt_tools = select(Tool).where(Tool.mcp_server_id == server_id)
    tools = session.exec(stmt_tools).all()
    for t in tools:
        session.delete(t)
        
    session.delete(server)
    session.commit()
    return None

@router.post("/servers/{server_id}/reload")
async def reload_server(
    *,
    session: Session = Depends(get_session),
    server_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Spawn/restart the MCP server subprocess and list discovered tools."""
    server = session.get(McpServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server configuration not found.")
    
    # Boot/reboot subprocess
    success = await mcp_manager.register_and_start(server, session)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start MCP server subprocess '{server.name}'. Check logs for details."
        )
        
    # Get tools list registered
    stmt_tools = select(Tool).where(Tool.mcp_server_id == server_id)
    tools = session.exec(stmt_tools).all()
    
    discovered_tools = [{"name": t.name, "description": t.description} for t in tools]
    
    return {
        "id": str(server.id),
        "name": server.name,
        "status": server.status,
        "tools_discovered": discovered_tools
    }
