from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.api.deps import get_current_user
from app.models.schemas import User, Agent, AgentCreate

router = APIRouter()

@router.get("", response_model=List[Agent])
def list_agents(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all configured custom agents."""
    statement = select(Agent)
    return session.exec(statement).all()

@router.post("", response_model=Agent, status_code=status.HTTP_201_CREATED)
def create_agent(
    *,
    session: Session = Depends(get_session),
    agent_in: AgentCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new agent profile."""
    db_agent = Agent.model_validate(agent_in)
    session.add(db_agent)
    session.commit()
    session.refresh(db_agent)
    return db_agent

@router.get("/{agent_id}", response_model=Agent)
def get_agent_by_id(
    *,
    session: Session = Depends(get_session),
    agent_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Retrieve a single agent profile."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    return agent

@router.put("/{agent_id}", response_model=Agent)
def update_agent(
    *,
    session: Session = Depends(get_session),
    agent_id: UUID,
    agent_in: AgentCreate,
    current_user: User = Depends(get_current_user)
):
    """Update configurations of an existing agent."""
    db_agent = session.get(Agent, agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    
    # Update fields dynamically
    update_data = agent_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_agent, key, value)
        
    session.add(db_agent)
    session.commit()
    session.refresh(db_agent)
    return db_agent

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    *,
    session: Session = Depends(get_session),
    agent_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Delete an agent configuration."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    session.delete(agent)
    session.commit()
    return None
