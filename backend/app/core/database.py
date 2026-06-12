from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

# In production, check if PostgreSQL is used
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, echo=False)

def create_db_and_tables():
    # Automatically creates all SQLModel structures on startup
    # Note: Import models here to register them with metadata
    from app.models.schemas import User, Folder, Agent, Tool, Conversation, Message, McpServer, Workflow, WorkflowExecution, AuditLog
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
