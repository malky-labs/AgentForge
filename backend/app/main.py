import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.api.router import api_router

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentForge")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Forge Intelligent Agents Locally - Orchestration API",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security policies
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    logger.info("Initializing AgentForge Database...")
    create_db_and_tables()
    logger.info("AgentForge Platform Backend is Online!")

# Mount API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AgentForge Core Orchestrator",
        "version": "0.1.0",
        "tagline": "Forge Intelligent Agents Locally."
    }

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy"}

# WebSocket Manager for chat events (Will refactor in Phase 2)
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.websocket("/api/v1/ws/chat/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    await manager.connect(websocket)
    logger.info(f"WebSocket connected for conversation: {conversation_id}")
    try:
        while True:
            # Handle incoming client commands
            data = await websocket.receive_text()
            logger.info(f"Received from client in {conversation_id}: {data}")
            
            # Streaming mock tokens back as proof-of-concept
            await manager.send_personal_message(
                f'{{"type": "token", "content": "Acknowledged: \'{data}\'. Processing local inference agent task..."}}', 
                websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected for conversation: {conversation_id}")
