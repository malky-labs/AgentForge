import asyncio
import json
import logging
import shlex
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlmodel import Session, select
from app.models.schemas import McpServer, Tool

logger = logging.getLogger("AgentForge.MCP")

class McpClient:
    def __init__(self, server_id: str, name: str, command: str, args: List[str], env: Dict[str, str] = None):
        self.server_id = server_id
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.read_task: Optional[asyncio.Task] = None

    async def start(self) -> bool:
        """Spawn the MCP server subprocess and start standard I/O loops."""
        logger.info(f"Starting MCP server subprocess '{self.name}': {self.command} {' '.join(self.args)}")
        try:
            # On Windows, we need shell=True or appropriate execution for scripts like npx
            # Use shell execution to allow shell commands like 'npx' directly
            full_cmd = f"{self.command} {' '.join(shlex.quote(a) for a in self.args)}"
            
            self.process = await asyncio.create_subprocess_shell(
                full_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env
            )
            
            # Start background reader task
            self.read_task = asyncio.create_task(self._read_stdout_loop())
            asyncio.create_task(self._read_stderr_loop())
            
            # Send initialize handshake
            init_res = await self.call_method("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "AgentForge", "version": "0.1.0"}
            })
            
            # Send initialized notification
            await self.send_notification("initialized", {})
            logger.info(f"MCP server '{self.name}' initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP server '{self.name}': {e}")
            await self.stop()
            return False

    async def stop(self):
        """Terminate the subprocess and close connection streams."""
        if self.read_task:
            self.read_task.cancel()
            self.read_task = None
            
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass
            self.process = None
            
        # Fail any pending futures
        for fut in self.pending_requests.values():
            if not fut.done():
                fut.set_exception(Exception("MCP Server stopped"))
        self.pending_requests.clear()
        logger.info(f"MCP server '{self.name}' stopped.")

    async def call_method(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a JSON-RPC 2.0 request and await the response."""
        if not self.process or not self.process.stdin:
            raise Exception("MCP server process is not running")

        self.request_id += 1
        rid = self.request_id
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": rid
        }
        
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_requests[rid] = future
        
        # Write payload + newline
        raw = json.dumps(payload) + "\n"
        self.process.stdin.write(raw.encode('utf-8'))
        await self.process.stdin.drain()
        
        # Await response with timeout
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self.pending_requests.pop(rid, None)
            raise Exception(f"MCP call to method '{method}' timed out after 30 seconds.")

    async def send_notification(self, method: str, params: Dict[str, Any]):
        """Send a JSON-RPC 2.0 notification (no response expected)."""
        if not self.process or not self.process.stdin:
            return
            
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        raw = json.dumps(payload) + "\n"
        self.process.stdin.write(raw.encode('utf-8'))
        await self.process.stdin.drain()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Query the tools list from the MCP server."""
        try:
            res = await self.call_method("tools/list", {})
            return res.get("result", {}).get("tools", [])
        except Exception as e:
            logger.error(f"Error listing tools for '{self.name}': {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger an execution of an MCP tool."""
        try:
            res = await self.call_method("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            return res.get("result", {})
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}' on '{self.name}': {e}")
            return {"isError": True, "content": [{"type": "text", "text": f"Execution error: {str(e)}"}]}

    async def _read_stdout_loop(self):
        """Asynchronous reader task decoding JSON-RPC responses from stdout."""
        try:
            while self.process and self.process.stdout:
                line_bytes = await self.process.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode('utf-8').strip()
                if not line:
                    continue
                
                try:
                    payload = json.loads(line)
                    # Handle response matching
                    rid = payload.get("id")
                    if rid in self.pending_requests:
                        future = self.pending_requests.pop(rid)
                        if "error" in payload:
                            future.set_exception(Exception(payload["error"].get("message", "Unknown error")))
                        else:
                            future.set_result(payload)
                except Exception as e:
                    logger.debug(f"Non-JSON-RPC stdout from '{self.name}': {line}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Stdout reader crash in '{self.name}': {e}")

    async def _read_stderr_loop(self):
        """Asynchronous reader log routing for subprocess stderr streams."""
        try:
            while self.process and self.process.stderr:
                line_bytes = await self.process.stderr.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode('utf-8').strip()
                if line:
                    logger.debug(f"[{self.name} STDERR] {line}")
        except Exception:
            pass


class McpManager:
    def __init__(self):
        # Maps server_id -> McpClient
        self.clients: Dict[str, McpClient] = {}

    async def register_and_start(self, server: McpServer, session: Session) -> bool:
        """Boot a newly registered MCP server subprocess and catalog its tools."""
        # Clean up if existing
        sid = str(server.id)
        if sid in self.clients:
            await self.clients[sid].stop()
            
        args_list = json.loads(server.args)
        env_dict = json.loads(server.env)
        
        client = McpClient(
            server_id=sid,
            name=server.name,
            command=server.command,
            args=args_list,
            env=env_dict
        )
        
        success = await client.start()
        if success:
            self.clients[sid] = client
            server.status = "running"
            session.add(server)
            session.commit()
            
            # Sync discovered tools to DB
            tools = await client.list_tools()
            for t in tools:
                # Upsert tool definition
                existing_tool_stmt = select(Tool).where(Tool.name == t["name"])
                existing_tool = session.exec(existing_tool_stmt).first()
                
                tool_schema = json.dumps(t.get("inputSchema", {}))
                
                if existing_tool:
                    existing_tool.description = t.get("description", "")
                    existing_tool.schema_json = tool_schema
                    existing_tool.mcp_server_id = server.id
                    session.add(existing_tool)
                else:
                    new_tool = Tool(
                        name=t["name"],
                        description=t.get("description", ""),
                        schema_json=tool_schema,
                        tool_type="mcp",
                        mcp_server_id=server.id
                    )
                    session.add(new_tool)
            session.commit()
            return True
        else:
            server.status = "error"
            session.add(server)
            session.commit()
            return False

    async def stop_server(self, server_id: str, session: Session):
        """Shutdown an active MCP server connection."""
        sid = str(server_id)
        if sid in self.clients:
            await self.clients[sid].stop()
            del self.clients[sid]
            
        server = session.get(McpServer, server_id)
        if server:
            server.status = "offline"
            session.add(server)
            session.commit()

    async def get_tool_client(self, tool_name: str, session: Session) -> Optional[McpClient]:
        """Locate the client running the requested tool."""
        stmt = select(Tool).where(Tool.name == tool_name)
        tool = session.exec(stmt).first()
        if tool and tool.mcp_server_id:
            sid = str(tool.mcp_server_id)
            if sid in self.clients:
                return self.clients[sid]
        return None

    async def shutdown_all(self):
        """Gracefully terminate all running subprocesses on system exit."""
        logger.info("Stopping all active MCP client sessions...")
        for client in list(self.clients.values()):
            await client.stop()
        self.clients.clear()

mcp_manager = McpManager()
