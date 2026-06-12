import asyncio
import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
from app.services.webhook_dispatcher import webhook_dispatcher

logger = logging.getLogger("AgentForge.Runtime")

class AgentSession:
    def __init__(self, session_id: str, agent_id: str):
        self.session_id = session_id
        self.agent_id = agent_id
        self.state = "idle" # idle, running, waiting_for_tool, responding, completed, failed
        self.history: List[Dict[str, str]] = []
        self.current_task: Optional[asyncio.Task] = None

class EventBus:
    def __init__(self):
        # Maps session_id -> list of asyncio.Queue subscribers
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue:
        """Register a subscriber queue for real-time logs and tokens."""
        queue = asyncio.Queue()
        if session_id not in self.subscribers:
            self.subscribers[session_id] = []
        self.subscribers[session_id].append(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        """Unsubscribe and cleanup queue listeners."""
        if session_id in self.subscribers:
            try:
                self.subscribers[session_id].remove(queue)
            except ValueError:
                pass
            if not self.subscribers[session_id]:
                del self.subscribers[session_id]

    async def publish(self, session_id: str, event: Dict[str, Any]):
        """Broadcast an execution event to all listeners of a session."""
        if session_id in self.subscribers:
            # Publish to all registered queues
            for queue in self.subscribers[session_id]:
                await queue.put(event)


class AgentMessageChannel:
    def __init__(self):
        # Maps topic_name -> list of asyncio.Queue subscribers
        self.topics: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, topic: str) -> asyncio.Queue:
        """Subscribe to an agent messaging channel topic."""
        queue = asyncio.Queue()
        if topic not in self.topics:
            self.topics[topic] = []
        self.topics[topic].append(queue)
        logger.info(f"Subscribed queue to topic '{topic}'")
        return queue

    def unsubscribe(self, topic: str, queue: asyncio.Queue):
        """Unsubscribe queue from topic."""
        if topic in self.topics:
            try:
                self.topics[topic].remove(queue)
            except ValueError:
                pass
            if not self.topics[topic]:
                del self.topics[topic]

    async def publish(self, topic: str, message: Dict[str, Any]):
        """Broadcast a message payload to all subscribers on the topic."""
        if topic in self.topics:
            for queue in self.topics[topic]:
                await queue.put(message)
            logger.info(f"Broadcast message to {len(self.topics[topic])} subscribers on topic '{topic}'")


class AgentSessionManager:
    def __init__(self):
        # Maps session_id -> AgentSession
        self.sessions: Dict[str, AgentSession] = {}
        self.event_bus = EventBus()
        self.message_channel = AgentMessageChannel()

    async def create_session(self, session_id: str, agent_id: str) -> AgentSession:
        """Initialize and register a new agent execution session."""
        if session_id in self.sessions:
            # Cancel old task if still running
            old_session = self.sessions[session_id]
            if old_session.current_task and not old_session.current_task.done():
                old_session.current_task.cancel()
                
        session = AgentSession(session_id, agent_id)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Fetch session information."""
        return self.sessions.get(session_id)

    def update_state(self, session_id: str, state: str):
        """Update state machine state."""
        if session_id in self.sessions:
            self.sessions[session_id].state = state
            logger.info(f"Session '{session_id}' state updated: {state.upper()}")

    async def run_agent_job(
        self,
        session_id: str,
        agent_id: str,
        messages: List[Dict[str, str]],
        session_db_factory
    ):
        """Run agent task in a decoupled background loop publishing updates to EventBus."""
        session = await self.create_session(session_id, agent_id)
        
        # Define background worker task
        async def worker():
            from app.services.agent_runner import agent_runner
            from app.models.schemas import Agent
            
            self.update_state(session_id, "running")
            await self.event_bus.publish(session_id, {"type": "status", "content": "Starting agent execution..."})
            
            # Open direct session using factory
            with session_db_factory() as db_session:
                from uuid import UUID as uuid_cast
                agent = db_session.get(Agent, uuid_cast(agent_id))
                if not agent:
                    self.update_state(session_id, "failed")
                    await self.event_bus.publish(session_id, {"type": "error", "content": "Agent profile not found."})
                    return
                
                try:
                    response_content = ""
                    async for chunk in agent_runner.execute_react_loop(
                        agent=agent,
                        conversation_history=messages,
                        session=db_session
                    ):
                        # Translate states
                        if chunk["type"] == "token":
                            response_content += chunk["content"]
                            self.update_state(session_id, "responding")
                            await self.event_bus.publish(session_id, chunk)
                        elif chunk["type"] == "tool_start":
                            self.update_state(session_id, "waiting_for_tool")
                            await self.event_bus.publish(session_id, chunk)
                        elif chunk["type"] == "tool_end":
                            self.update_state(session_id, "running")
                            await self.event_bus.publish(session_id, chunk)
                        elif chunk["type"] == "final_answer":
                            response_content = chunk["content"]
                            self.update_state(session_id, "completed")
                            await self.event_bus.publish(session_id, {
                                "type": "done",
                                "content": response_content
                            })
                            webhook_dispatcher.dispatch("agent.completed", {
                                "session_id": session_id,
                                "agent_id": agent_id,
                                "state": "completed",
                                "output": response_content
                            })
                        elif chunk["type"] == "error":
                            self.update_state(session_id, "failed")
                            await self.event_bus.publish(session_id, chunk)
                            webhook_dispatcher.dispatch("agent.failed", {
                                "session_id": session_id,
                                "agent_id": agent_id,
                                "state": "failed",
                                "error": chunk["content"]
                            })
                            return
                            
                except Exception as e:
                    logger.exception(f"Unhandled crash in agent worker session '{session_id}':")
                    self.update_state(session_id, "failed")
                    await self.event_bus.publish(session_id, {"type": "error", "content": f"Worker Exception: {str(e)}"})
                    webhook_dispatcher.dispatch("agent.failed", {
                        "session_id": session_id,
                        "agent_id": agent_id,
                        "state": "failed",
                        "error": str(e)
                    })

        # Start job in background task
        task = asyncio.create_task(worker())
        session.current_task = task
        return session

runtime_engine = AgentSessionManager()
