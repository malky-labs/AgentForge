from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship

# --- User Model ---
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    full_name: Optional[str] = None
    role: str = Field(default="user")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# --- Folder Model ---
class Folder(SQLModel, table=True):
    __tablename__ = "folders"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False)
    parent_id: Optional[UUID] = Field(default=None, foreign_key="folders.id")
    user_id: UUID = Field(foreign_key="users.id")
    type: str = Field(nullable=False) # 'chat' or 'workflow'
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Agent-Tool Many-To-Many Link ---
class AgentToolLink(SQLModel, table=True):
    __tablename__ = "agent_tool_link"
    agent_id: UUID = Field(foreign_key="agents.id", primary_key=True)
    tool_id: UUID = Field(foreign_key="tools.id", primary_key=True)

# --- Agent Model ---
class Agent(SQLModel, table=True):
    __tablename__ = "agents"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False)
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    system_prompt: str = Field(nullable=False)
    model_provider: str = Field(nullable=False) # 'ollama', 'openai', 'gemini'
    model_name: str = Field(nullable=False)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2048)
    memory_limit: int = Field(default=10)
    permissions: str = Field(default="{}") # JSON String for sandbox permissions
    knowledge_collection_id: Optional[UUID] = Field(default=None, foreign_key="knowledge_collections.id")

# --- Tool Model ---
class Tool(SQLModel, table=True):
    __tablename__ = "tools"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, nullable=False)
    description: str = Field(nullable=False)
    schema_json: str = Field(nullable=False) # JSON schema for tool invocation inputs
    tool_type: str = Field(nullable=False)   # 'system', 'mcp', 'custom_python', 'rest'
    mcp_server_id: Optional[UUID] = Field(default=None, foreign_key="mcp_servers.id")
    config: str = Field(default="{}")         # API credentials or connection URLs
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Conversation Model ---
class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(nullable=False)
    user_id: UUID = Field(foreign_key="users.id")
    folder_id: Optional[UUID] = Field(default=None, foreign_key="folders.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# --- Message Model ---
class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    conversation_id: UUID = Field(foreign_key="conversations.id")
    sender_type: str = Field(nullable=False) # 'user', 'assistant', 'system', 'tool'
    sender_id: Optional[UUID] = None         # Holds Agent ID if sender is assistant
    content: str = Field(nullable=False)
    tokens_used: int = Field(default=0)
    extra_metadata: str = Field(default="{}")      # Holds tool logs, image generations
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- MCP Server Model ---
class McpServer(SQLModel, table=True):
    __tablename__ = "mcp_servers"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True, nullable=False)
    command: str = Field(nullable=False)
    args: str = Field(default="[]")          # JSON array of command CLI parameters
    env: str = Field(default="{}")           # Encrypted JSON string of env settings
    status: str = Field(default="offline")   # 'running', 'error', 'offline'
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Workflow Model ---
class Workflow(SQLModel, table=True):
    __tablename__ = "workflows"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False)
    description: Optional[str] = None
    graph_json: str = Field(nullable=False) # Visual React Flow Nodes JSON representation
    is_active: bool = Field(default=True)
    trigger_type: str = Field(default="manual") # 'manual', 'webhook', 'cron'
    folder_id: Optional[UUID] = Field(default=None, foreign_key="folders.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# --- Workflow Execution Log Model ---
class WorkflowExecution(SQLModel, table=True):
    __tablename__ = "workflow_executions"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflows.id")
    state: str = Field(nullable=False)      # 'pending', 'running', 'completed', 'failed'
    input_data: str = Field(default="{}")
    output_data: str = Field(default="{}")
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None

# --- Audit Log Model ---
class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    action: str = Field(nullable=False)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- Agent Session Record Model ---
class AgentSessionRecord(SQLModel, table=True):
    __tablename__ = "agent_session_records"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agent_id: UUID = Field(foreign_key="agents.id")
    state: str = Field(default="idle")  # 'idle', 'running', 'waiting_for_tool', 'responding', 'completed', 'failed'
    history: str = Field(default="[]")  # JSON string conversation history
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Scheduled Job Model ---
class ScheduledJob(SQLModel, table=True):
    __tablename__ = "scheduled_jobs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False)
    cron_expression: Optional[str] = None  # e.g., "*/5 * * * *"
    task_type: str = Field(nullable=False)  # 'agent_run', 'workflow_run'
    target_id: UUID = Field(nullable=False)  # Agent ID or Workflow ID
    payload: str = Field(default="{}")
    next_run_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Job Run Log Model ---
class JobRun(SQLModel, table=True):
    __tablename__ = "job_runs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_id: UUID = Field(foreign_key="scheduled_jobs.id")
    state: str = Field(nullable=False)  # 'running', 'completed', 'failed'
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


# --- Knowledge Collection Model ---
class KnowledgeCollection(SQLModel, table=True):
    __tablename__ = "knowledge_collections"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True)
    description: Optional[str] = None
    user_id: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- Knowledge Document Model ---
class KnowledgeDocument(SQLModel, table=True):
    __tablename__ = "knowledge_documents"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    collection_id: UUID = Field(foreign_key="knowledge_collections.id")
    name: str = Field(nullable=False)
    file_path: Optional[str] = None
    file_type: str = Field(nullable=False)  # 'pdf', 'md', 'web'
    size_bytes: int = Field(default=0)
    status: str = Field(default="pending")  # 'pending', 'processing', 'completed', 'failed'
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Workflow Node Execution Log Model ---
class WorkflowNodeExecutionLog(SQLModel, table=True):
    __tablename__ = "workflow_node_execution_logs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_execution_id: UUID = Field(foreign_key="workflow_executions.id")
    node_id: str = Field(nullable=False)
    node_name: str = Field(nullable=False)
    node_type: str = Field(nullable=False)
    state: str = Field(nullable=False)  # 'pending', 'running', 'completed', 'failed'
    input_data: Optional[str] = "{}"
    output_data: Optional[str] = "{}"
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    retries_count: int = Field(default=0)


# --- Webhook Subscription Model ---
class WebhookSubscription(SQLModel, table=True):
    __tablename__ = "webhook_subscriptions"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    target_url: str = Field(nullable=False)
    event_type: str = Field(nullable=False)  # 'agent.completed', 'workflow.failed', '*'
    is_active: bool = Field(default=True)
    secret_token: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Webhook Delivery Log Model ---
class WebhookDeliveryLog(SQLModel, table=True):
    __tablename__ = "webhook_delivery_logs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    subscription_id: UUID = Field(foreign_key="webhook_subscriptions.id")
    event_type: str = Field(nullable=False)
    payload: str = Field(nullable=False)
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Request & Response Schemas (Non-Table Models) ---
class UserCreate(SQLModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserRead(SQLModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime


class Token(SQLModel):
    access_token: str
    token_type: str


class AgentCreate(SQLModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    model_provider: str = "ollama"
    model_name: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    memory_limit: Optional[int] = 10
    permissions: Optional[str] = "{}"
    knowledge_collection_id: Optional[UUID] = None


class McpServerCreate(SQLModel):
    name: str
    command: str
    args: Optional[str] = "[]"
    env: Optional[str] = "{}"


class WorkflowCreate(SQLModel):
    name: str
    description: Optional[str] = None
    graph_json: str
    is_active: Optional[bool] = True
    trigger_type: Optional[str] = "manual"


class KnowledgeCollectionCreate(SQLModel):
    name: str
    description: Optional[str] = None


class WebhookSubscriptionCreate(SQLModel):
    target_url: str
    event_type: str = "*"
    secret_token: Optional[str] = None


class ScheduledJobCreate(SQLModel):
    name: str
    cron_expression: Optional[str] = None
    task_type: str  # 'agent_run', 'workflow_run'
    target_id: UUID
    payload: Optional[str] = "{}"





