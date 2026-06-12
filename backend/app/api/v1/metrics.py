from fastapi import APIRouter, Depends
from sqlmodel import Session, func, select
from app.core.database import get_session
from app.models.schemas import User, Agent, Conversation, Message, Workflow, WorkflowExecution

router = APIRouter()

@router.get("")
def read_system_metrics(session: Session = Depends(get_session)):
    """Aggregate statistics on system configurations, executions, and database size."""
    users_count = session.exec(select(func.count(User.id))).one()
    agents_count = session.exec(select(func.count(Agent.id))).one()
    convs_count = session.exec(select(func.count(Conversation.id))).one()
    messages_count = session.exec(select(func.count(Message.id))).one()
    workflows_count = session.exec(select(func.count(Workflow.id))).one()
    executions_count = session.exec(select(func.count(WorkflowExecution.id))).one()
    
    # Custom simple Prometheus format option or direct JSON
    return {
        "metrics": {
            "users_total": users_count,
            "agents_total": agents_count,
            "conversations_total": convs_count,
            "messages_total": messages_count,
            "workflows_total": workflows_count,
            "workflow_executions_total": executions_count
        }
    }
