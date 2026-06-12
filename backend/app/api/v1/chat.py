import json
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, status
from jose import jwt, JWTError
from sqlmodel import Session, select
from app.core.config import settings
from app.core.database import get_session
from app.api.deps import get_current_user
from app.models.schemas import Conversation, Message, User, Agent
from app.services.ollama import ollama_service

logger = logging.getLogger("AgentForge.Chat")
router = APIRouter()

# --- Connection Manager for WebSockets ---
class ChatConnectionManager:
    def __init__(self):
        # Maps conversation_id -> list of WebSockets
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)

    def disconnect(self, websocket: WebSocket, conversation_id: str):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

    async def broadcast_to_conversation(self, conversation_id: str, message: dict):
        if conversation_id in self.active_connections:
            payload = json.dumps(message)
            for connection in self.active_connections[conversation_id]:
                await connection.send_text(payload)

manager = ChatConnectionManager()

# --- REST Endpoints ---

@router.post("/conversations", response_model=Conversation, status_code=status.HTTP_201_CREATED)
def create_conversation(
    *,
    session: Session = Depends(get_session),
    title: str,
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation room."""
    db_conv = Conversation(title=title, user_id=current_user.id)
    session.add(db_conv)
    session.commit()
    session.refresh(db_conv)
    return db_conv

@router.get("/conversations", response_model=List[Conversation])
def list_conversations(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List all conversations for the active user."""
    statement = select(Conversation).where(Conversation.user_id == current_user.id).order_by(Conversation.created_at.desc())
    return session.exec(statement).all()

@router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
def list_messages(
    *,
    session: Session = Depends(get_session),
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get message history for a conversation."""
    # Ensure conversation exists and belongs to current user
    conv = session.get(Conversation, conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    statement = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    return session.exec(statement).all()

# --- WebSocket Endpoint ---

@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    token: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """Real-time two-way WebSocket for local/cloud LLM inference streaming."""
    # 1. Authenticate user from the token in query parameter
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token required")
        return

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return
        from uuid import UUID as uuid_cast
        user_uuid = uuid_cast(user_id)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    # Check database for user validity
    db_user = session.get(User, user_uuid)
    if not db_user or not db_user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User deactivated")
        return

    # Validate conversation room
    try:
        conv_uuid = uuid_cast(conversation_id)
    except ValueError:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason="Invalid conversation ID")
        return

    conv = session.get(Conversation, conv_uuid)
    if not conv or conv.user_id != db_user.id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access denied")
        return

    # 2. Register socket connection
    await manager.connect(websocket, conversation_id)
    logger.info(f"User {db_user.email} joined chat: {conversation_id}")

    try:
        while True:
            # Receive text data
            data = await websocket.receive_text()
            try:
                msg_payload = json.loads(data)
                user_content = msg_payload.get("content", "").strip()
                agent_id_str = msg_payload.get("agent_id")
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "content": "Invalid JSON format"}))
                continue

            if not user_content:
                continue

            # Save user message to database and index in memory
            user_msg = Message(
                conversation_id=conv_uuid,
                sender_type="user",
                content=user_content,
            )
            session.add(user_msg)
            session.commit()
            session.refresh(user_msg)

            from app.services.memory_service import memory_service
            await memory_service.index_message(
                conversation_id=str(conv_uuid),
                message_id=str(user_msg.id),
                sender_type="user",
                content=user_content
            )

            # Retrieve active agent parameters
            agent = None
            if agent_id_str:
                try:
                    agent = session.get(Agent, uuid_cast(agent_id_str))
                except ValueError:
                    pass

            system_prompt = "You are a helpful assistant."
            model_name = "llama3:8b" # default model fallback
            temperature = 0.7

            if agent:
                system_prompt = agent.system_prompt
                model_name = agent.model_name
                temperature = agent.temperature

            # Inject semantic memory matching context
            context_injection = await memory_service.get_context_injection(
                conversation_id=str(conv_uuid),
                query=user_content
            )
            system_prompt = system_prompt + context_injection

            # Assemble short-term message history
            statement = select(Message).where(Message.conversation_id == conv_uuid).order_by(Message.created_at.desc()).limit(15)
            history_msgs = list(reversed(session.exec(statement).all()))

            # Format payload for Ollama
            ollama_messages = [{"role": "system", "content": system_prompt}]
            for h in history_msgs:
                role = "user" if h.sender_type == "user" else "assistant"
                ollama_messages.append({"role": role, "content": h.content})

            # Check if Ollama is healthy before starting completion
            if not await ollama_service.is_healthy():
                err_msg = "Error: Local Ollama service is unreachable. Make sure Ollama is running (`ollama serve`)."
                await websocket.send_text(json.dumps({"type": "error", "content": err_msg}))
                continue

            # Stream response back
            response_content = ""
            if agent:
                from app.services.agent_runner import agent_runner
                async for chunk in agent_runner.execute_react_loop(
                    agent=agent,
                    conversation_history=ollama_messages[1:],
                    session=session
                ):
                    if chunk["type"] == "token":
                        response_content += chunk["content"]
                        await websocket.send_text(json.dumps({
                            "type": "token",
                            "content": chunk["content"]
                        }))
                    elif chunk["type"] == "tool_start":
                        await websocket.send_text(json.dumps({
                            "type": "tool_start",
                            "tool_name": chunk["tool_name"],
                            "arguments": chunk["arguments"]
                        }))
                    elif chunk["type"] == "tool_end":
                        await websocket.send_text(json.dumps({
                            "type": "tool_end",
                            "tool_name": chunk["tool_name"],
                            "status": chunk["status"],
                            "result": chunk["result"]
                        }))
                    elif chunk["type"] == "final_answer":
                        response_content = chunk["content"]
                    elif chunk["type"] == "error":
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "content": chunk["content"]
                        }))
            else:
                async for token_chunk in ollama_service.chat_completion_stream(
                    model=model_name,
                    messages=ollama_messages,
                    options={"temperature": temperature}
                ):
                    if token_chunk.get("type") == "token":
                        response_content += token_chunk["content"]
                        await websocket.send_text(json.dumps({
                            "type": "token",
                            "content": token_chunk["content"]
                        }))
                    elif token_chunk.get("type") == "error":
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "content": token_chunk["content"]
                        }))

            # Save complete assistant response and index in memory
            if response_content:
                assistant_msg = Message(
                    conversation_id=conv_uuid,
                    sender_type="assistant",
                    sender_id=agent.id if agent else None,
                    content=response_content
                )
                session.add(assistant_msg)
                session.commit()
                session.refresh(assistant_msg)
                
                await memory_service.index_message(
                    conversation_id=str(conv_uuid),
                    message_id=str(assistant_msg.id),
                    sender_type="assistant",
                    content=response_content
                )
                
                # Signal completion
                await websocket.send_text(json.dumps({
                    "type": "done",
                    "message_id": str(assistant_msg.id),
                    "content": response_content
                }))

    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
        logger.info(f"WebSocket disconnected from conversation: {conversation_id}")
