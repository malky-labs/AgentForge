from fastapi import APIRouter
from app.api.v1 import auth, hub, chat, agents, mcp, workflows

api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(hub.router, prefix="/hub", tags=["hub"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
