import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import deque
from sqlmodel import Session, select
from app.models.schemas import Workflow, WorkflowExecution, Agent, Tool
from app.services.agent_runner import agent_runner
from app.services.mcp_manager import mcp_manager
from app.services.ollama import ollama_service

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
            execution_order = self.check_for_cycles(nodes, adj_list, in_degrees)
        except Exception as e:
            execution.state = "failed"
            execution.error_message = str(e)
            execution.finished_at = datetime.utcnow()
            session.add(execution)
            session.commit()
            return

        # Execute node by node topologically
        node_outputs: Dict[str, Any] = {}
        
        try:
            for node_id in execution_order:
                node = nodes[node_id]
                node_type = node.get("type")
                node_data = node.get("data", {})
                
                logger.info(f"Executing workflow node: {node_id} (Type: {node_type})")
                
                # Fetch inputs from parent nodes if configured
                input_prompt = node_data.get("prompt", "")
                
                # If there is parent context, prepend it
                parent_context = ""
                for n_src, targets in adj_list.items():
                    if node_id in targets and n_src in node_outputs:
                        parent_context += f"\n[Context from parent node '{nodes[n_src].get('data', {}).get('name', n_src)}']:\n{node_outputs[n_src]}\n"
                
                if parent_context:
                    input_prompt = f"{parent_context}\nTask prompt: {input_prompt}"

                output_str = ""

                if node_type == "agentNode":
                    # Execute Agent persona loop
                    agent_id = node_data.get("agentId")
                    if not agent_id:
                        raise Exception(f"AgentNode '{node_id}' is missing a configured agent persona.")
                    
                    from uuid import UUID as uuid_cast
                    agent = session.get(Agent, uuid_cast(agent_id))
                    if not agent:
                        raise Exception(f"Agent persona '{agent_id}' linked to node '{node_id}' does not exist.")
                    
                    history = [{"role": "user", "content": input_prompt}]
                    
                    # Call ReAct executor
                    last_chunk = None
                    async for chunk in agent_runner.execute_react_loop(
                        agent=agent,
                        conversation_history=history,
                        session=session
                    ):
                        if chunk["type"] == "final_answer":
                            output_str = chunk["content"]
                        elif chunk["type"] == "error":
                            raise Exception(f"Agent loop error inside node '{node_id}': {chunk['content']}")
                    
                    if not output_str:
                        output_str = "Agent completed execution with no response."

                elif node_type == "toolNode":
                    # Direct tool execution
                    tool_name = node_data.get("toolName")
                    if not tool_name:
                        raise Exception(f"ToolNode '{node_id}' has no toolName specified.")
                    
                    tool_args = node_data.get("arguments", {})
                    # If arguments contain variables, interpolate them from context state
                    # For simplicity, we directly execute with args
                    
                    if tool_name == "python_sandbox":
                        code = tool_args.get("code", "")
                        from app.services.agent_runner import execute_python_sandbox
                        output_str = await execute_python_sandbox(code)
                    else:
                        mcp_client = await mcp_manager.get_tool_client(tool_name, session)
                        if not mcp_client:
                            raise Exception(f"MCP client for tool '{tool_name}' is not running.")
                        
                        tool_result = await mcp_client.call_tool(tool_name, tool_args)
                        
                        # Extract text
                        content_blocks = tool_result.get("content", [])
                        for block in content_blocks:
                            if block.get("type") == "text":
                                output_str += block.get("text", "")
                        if not output_str:
                            output_str = json.dumps(tool_result)
                else:
                    # Generic / Unknown Node
                    output_str = f"Skipped node '{node_id}' of unknown type '{node_type}'."

                # Save output to carry forward
                node_outputs[node_id] = output_str
                context_state[node_id] = {
                    "status": "success",
                    "output": output_str
                }
            
            # Finished execution of all nodes
            execution.state = "completed"
            execution.output_data = json.dumps(node_outputs)
            execution.finished_at = datetime.utcnow()
            session.add(execution)
            session.commit()
            logger.info(f"Workflow execution {execution_id} completed successfully.")
            
        except Exception as err:
            logger.error(f"Workflow execution {execution_id} failed: {err}")
            execution.state = "failed"
            execution.error_message = str(err)
            execution.output_data = json.dumps(node_outputs)
            execution.finished_at = datetime.utcnow()
            session.add(execution)
            session.commit()

workflow_runner = WorkflowRunner()
