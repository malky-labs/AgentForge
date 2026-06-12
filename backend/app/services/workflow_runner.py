import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import deque
from sqlmodel import Session, select
from app.models.schemas import Workflow, WorkflowExecution, Agent, Tool, WorkflowNodeExecutionLog
from app.services.agent_runner import agent_runner
from app.services.mcp_manager import mcp_manager
from app.services.ollama import ollama_service
from app.services.webhook_dispatcher import webhook_dispatcher

logger = logging.getLogger("AgentForge.WorkflowRunner")

class WorkflowRunner:
    def __init__(self):
        pass

    def _parse_graph(self, graph_json_str: str) -> tuple[Dict[str, Dict[str, Any]], Dict[str, List[str]], Dict[str, int]]:
        """Convert React Flow nodes/edges JSON into an adjacency list and in-degrees representation."""
        try:
            graph = json.loads(graph_json_str)
        except json.JSONDecodeError:
            raise Exception("Invalid graph JSON format.")

        raw_nodes = graph.get("nodes", [])
        raw_edges = graph.get("edges", [])

        nodes: Dict[str, Dict[str, Any]] = {n["id"]: n for n in raw_nodes}
        adj_list: Dict[str, List[str]] = {n_id: [] for n_id in nodes}
        in_degrees: Dict[str, int] = {n_id: 0 for n_id in nodes}

        # Build connections
        for edge in raw_edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src in adj_list and tgt in in_degrees:
                adj_list[src].append(tgt)
                in_degrees[tgt] += 1

        return nodes, adj_list, in_degrees

    def check_for_cycles(self, nodes: Dict[str, Any], adj_list: Dict[str, List[str]], in_degrees: Dict[str, int]) -> List[str]:
        """Perform topological sort (Kahn's Algorithm) to discover if the graph has cycles."""
        in_deg = in_degrees.copy()
        queue = deque([n_id for n_id, deg in in_deg.items() if deg == 0])
        topo_order = []

        while queue:
            curr = queue.popleft()
            topo_order.append(curr)
            
            for neighbor in adj_list.get(curr, []):
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0:
                    queue.append(neighbor)

        if len(topo_order) != len(nodes):
            raise Exception("Cycle detected in the workflow graph. A workflow must be a Directed Acyclic Graph (DAG).")
            
        return topo_order

    async def execute_workflow(self, execution_id: str, session: Session):
        """Asynchronous execution task scheduler for the entire workflow sequence."""
        execution = session.get(WorkflowExecution, execution_id)
        if not execution:
            logger.error(f"Workflow execution '{execution_id}' not found.")
            return

        workflow = session.get(Workflow, execution.workflow_id)
        if not workflow:
            execution.state = "failed"
            execution.error_message = "Workflow blueprint deleted."
            execution.finished_at = datetime.utcnow()
            session.add(execution)
            session.commit()
            return

        logger.info(f"Starting workflow execution: {workflow.name} (Run: {execution_id})")
        execution.state = "running"
        session.add(execution)
        session.commit()

        # Variable flow dictionary passed along nodes
        context_state: Dict[str, Any] = {}
        if execution.input_data:
            try:
                context_state = json.loads(execution.input_data)
            except json.JSONDecodeError:
                pass

        try:
            nodes, adj_list, in_degrees = self._parse_graph(workflow.graph_json)
            self.check_for_cycles(nodes, adj_list, in_degrees)
        except Exception as e:
            execution.state = "failed"
            execution.error_message = str(e)
            execution.finished_at = datetime.utcnow()
            session.add(execution)
            session.commit()
            return

        # Setup parents mapping
        parents: Dict[str, List[str]] = {n_id: [] for n_id in nodes}
        for n_src, targets in adj_list.items():
            for tgt in targets:
                parents[tgt].append(n_src)

        node_states: Dict[str, str] = {n_id: "pending" for n_id in nodes}
        node_tasks: Dict[str, asyncio.Task] = {}
        node_outputs: Dict[str, Any] = {}

        async def run_single_node(node_id: str):
            node = nodes[node_id]
            node_type = node.get("type")
            node_data = node.get("data", {})

            # Setup checkpoint log
            db_log = WorkflowNodeExecutionLog(
                workflow_execution_id=execution.id,
                node_id=node_id,
                node_name=node_data.get("name", node_id),
                node_type=node_type,
                state="running",
                started_at=datetime.utcnow()
            )
            session.add(db_log)
            session.commit()
            session.refresh(db_log)

            max_retries = int(node_data.get("retries", 0))
            backoff_seconds = float(node_data.get("retry_backoff", 2.0))
            attempts = 0

            while True:
                try:
                    # Prepend parent output contexts
                    parent_context = ""
                    for p_id in parents[node_id]:
                        if p_id in node_outputs:
                            parent_context += f"\n[Context from parent node '{nodes[p_id].get('data', {}).get('name', p_id)}']:\n{node_outputs[p_id]}\n"

                    input_prompt = node_data.get("prompt", "")
                    if parent_context:
                        input_prompt = f"{parent_context}\nTask prompt: {input_prompt}"

                    db_log.input_data = input_prompt
                    session.add(db_log)
                    session.commit()

                    output_str = ""
                    if node_type == "agentNode":
                        agent_id = node_data.get("agentId")
                        if not agent_id:
                            raise Exception("AgentNode is missing configured agent persona.")

                        from uuid import UUID as uuid_cast
                        agent = session.get(Agent, uuid_cast(agent_id))
                        if not agent:
                            raise Exception(f"Agent persona '{agent_id}' does not exist.")

                        history = [{"role": "user", "content": input_prompt}]
                        async for chunk in agent_runner.execute_react_loop(
                            agent=agent,
                            conversation_history=history,
                            session=session
                        ):
                            if chunk["type"] == "final_answer":
                                output_str = chunk["content"]
                            elif chunk["type"] == "error":
                                raise Exception(f"Agent execution error: {chunk['content']}")

                        if not output_str:
                            output_str = "Agent completed execution with no response."

                    elif node_type == "toolNode":
                        tool_name = node_data.get("toolName")
                        if not tool_name:
                            raise Exception("ToolNode has no toolName specified.")

                        tool_args = node_data.get("arguments", {})
                        if tool_name == "python_sandbox":
                            code = tool_args.get("code", "")
                            from app.services.agent_runner import execute_python_sandbox
                            output_str = await execute_python_sandbox(code)
                        else:
                            mcp_client = await mcp_manager.get_tool_client(tool_name, session)
                            if not mcp_client:
                                raise Exception(f"MCP client for tool '{tool_name}' is not running.")
                            tool_result = await mcp_client.call_tool(tool_name, tool_args)

                            content_blocks = tool_result.get("content", [])
                            for block in content_blocks:
                                if block.get("type") == "text":
                                    output_str += block.get("text", "")
                            if not output_str:
                                output_str = json.dumps(tool_result)
                    else:
                        output_str = f"Skipped node '{node_id}' of unknown type '{node_type}'."

                    # Completed successfully
                    node_outputs[node_id] = output_str
                    db_log.state = "completed"
                    db_log.output_data = output_str
                    db_log.finished_at = datetime.utcnow()
                    session.add(db_log)
                    session.commit()
                    return output_str

                except Exception as node_err:
                    attempts += 1
                    db_log.retries_count = attempts
                    session.add(db_log)
                    session.commit()

                    if attempts <= max_retries:
                        logger.warning(f"Node '{node_id}' failed (attempt {attempts}/{max_retries+1}). Retrying in {backoff_seconds}s. Error: {node_err}")
                        await asyncio.sleep(backoff_seconds)
                        backoff_seconds *= 2  # Exponential backoff
                    else:
                        db_log.state = "failed"
                        db_log.error_message = str(node_err)
                        db_log.finished_at = datetime.utcnow()
                        session.add(db_log)
                        session.commit()
                        raise node_err

        try:
            # Parallel scheduling execution loop
            while len(node_outputs) < len(nodes):
                # 1. Identify pending nodes whose dependencies are all completed
                ready_nodes = []
                for n_id in nodes:
                    if node_states[n_id] == "pending":
                        if all(node_states[p_id] == "completed" for p_id in parents[n_id]):
                            ready_nodes.append(n_id)

                if ready_nodes:
                    for n_id in ready_nodes:
                        node_states[n_id] = "running"
                        node_tasks[n_id] = asyncio.create_task(run_single_node(n_id))

                # 2. Wait for any active running node task to complete
                running_tasks = {n_id: t for n_id, t in node_tasks.items() if not t.done()}
                if not running_tasks:
                    failed_nodes = [n_id for n_id in nodes if node_states[n_id] == "failed"]
                    if failed_nodes:
                        raise Exception(f"Workflow failed due to errors in nodes: {', '.join(failed_nodes)}")
                    break

                done, pending = await asyncio.wait(
                    running_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Update states of finished node tasks
                for n_id, t in running_tasks.items():
                    if t.done():
                        try:
                            t.result()
                            node_states[n_id] = "completed"
                        except Exception as e:
                            node_states[n_id] = "failed"
                            raise e

            # Successful completion
            execution.state = "completed"
            execution.output_data = json.dumps(node_outputs)
            execution.finished_at = datetime.utcnow()
            session.add(execution)
            session.commit()
            logger.info(f"Workflow execution {execution_id} completed successfully.")
            webhook_dispatcher.dispatch("workflow.completed", {
                "execution_id": str(execution_id),
                "workflow_id": str(workflow.id),
                "state": "completed",
                "output_data": node_outputs
            })

        except Exception as err:
            logger.error(f"Workflow execution {execution_id} failed: {err}")
            execution.state = "failed"
            execution.error_message = str(err)
            execution.output_data = json.dumps(node_outputs)
            execution.finished_at = datetime.utcnow()
            session.add(execution)
            session.commit()
            webhook_dispatcher.dispatch("workflow.failed", {
                "execution_id": str(execution_id),
                "workflow_id": str(workflow.id),
                "state": "failed",
                "error": str(err)
            })

workflow_runner = WorkflowRunner()
