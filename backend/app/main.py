import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.logging import setup_logging
from app.core.exceptions import register_exception_handlers
from app.core.middleware import RateLimitMiddleware
from app.api.router import api_router

# Initialize structured JSON logging
setup_logging()
logger = logging.getLogger("AgentForge")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Forge Intelligent Agents Locally - Production AI operating platform",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 1. Global Exception Handlers
register_exception_handlers(app)

# 2. Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)

# 3. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security policies
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.services.scheduler import scheduler

@app.on_event("startup")
def on_startup():
    logger.info("Initializing AgentForge Production Database Tables...")
    create_db_and_tables()
    scheduler.start()
    logger.info("AgentForge Platform Backend is Online!")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Stopping AgentForge platform components...")
    await scheduler.stop()

# 4. Mount versioned API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AgentForge Core Orchestrator",
        "version": "0.2.0",
        "tagline": "Forge Intelligent Agents Locally."
    }
