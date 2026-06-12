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

# Server is clean and modular. Routers are registered in api_router.
