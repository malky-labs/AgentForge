from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.api.deps import get_current_user
from app.models.schemas import User, Workflow, WorkflowCreate, WorkflowExecution
from app.services.workflow_runner import workflow_runner

router = APIRouter()

@router.get("", response_model=List[Workflow])
def list_workflows(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all visual workflows."""
    statement = select(Workflow).order_by(Workflow.created_at.desc())
    return session.exec(statement).all()

@router.post("", response_model=Workflow, status_code=status.HTTP_201_CREATED)
def create_workflow(
    *,
    session: Session = Depends(get_session),
    workflow_in: WorkflowCreate,
    current_user: User = Depends(get_current_user)
):
    """Save a new workflow blueprint."""
    db_wf = Workflow.model_validate(workflow_in)
    session.add(db_wf)
    session.commit()
    session.refresh(db_wf)
    return db_wf

@router.get("/{workflow_id}", response_model=Workflow)
def get_workflow_by_id(
    *,
    session: Session = Depends(get_session),
    workflow_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Retrieve details for a single workflow blueprint."""
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow blueprint not found.")
    return wf

@router.put("/{workflow_id}", response_model=Workflow)
def update_workflow(
    *,
    session: Session = Depends(get_session),
    workflow_id: UUID,
    workflow_in: WorkflowCreate,
    current_user: User = Depends(get_current_user)
):
    """Modify graph structure of an existing workflow."""
    db_wf = session.get(Workflow, workflow_id)
    if not db_wf:
        raise HTTPException(status_code=404, detail="Workflow blueprint not found.")
        
    update_data = workflow_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_wf, key, value)
        
    db_wf.updated_at = datetime.utcnow()
    session.add(db_wf)
    session.commit()
    session.refresh(db_wf)
    return db_wf

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    *,
    session: Session = Depends(get_session),
    workflow_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Delete a workflow blueprint configuration."""
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow blueprint not found.")
    
    # Delete associated execution logs
    stmt_execs = select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
    execs = session.exec(stmt_execs).all()
    for e in execs:
        session.delete(e)

    session.delete(wf)
    session.commit()
    return None

@router.post("/{workflow_id}/execute", response_model=WorkflowExecution, status_code=status.HTTP_202_ACCEPTED)
def execute_workflow_trigger(
    *,
    session: Session = Depends(get_session),
    workflow_id: UUID,
    background_tasks: BackgroundTasks,
    input_data: Optional[str] = "{}",
    current_user: User = Depends(get_current_user)
):
    """Trigger background execution sequence for a visual workflow DAG."""
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow blueprint not found.")

    # Create run entry in pending state
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        state="pending",
        input_data=input_data,
        started_at=datetime.utcnow()
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)

    # Schedule run sequence asynchronously
    background_tasks.add_task(
        workflow_runner.execute_workflow,
        execution_id=execution.id,
        session=session
    )

    return execution

@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecution])
def list_workflow_executions(
    *,
    session: Session = Depends(get_session),
    workflow_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get history log details of execution runs for a workflow."""
    statement = select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id).order_by(WorkflowExecution.started_at.desc())
    return session.exec(statement).all()
