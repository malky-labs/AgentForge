import asyncio
import json
import logging
import re
import os
import sys
import tempfile
from typing import AsyncGenerator, Dict, Any, List, Optional
from uuid import UUID
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.schemas import Tool, Agent
from app.services.ollama import ollama_service
from app.services.mcp_manager import mcp_manager

logger = logging.getLogger("AgentForge.AgentRunner")

async def execute_python_sandbox(code: str) -> str:
    """Run Python code inside an isolated subprocess with timeout."""
    try:
        # Create temp folder inside workspace
        temp_dir = "./scratch"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Write to script
        fd, temp_file_path = tempfile.mkstemp(suffix=".py", dir=temp_dir)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Execute script via subprocess
            proc = await asyncio.create_subprocess_exec(
                sys.executable, temp_file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=8.0)
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
                
                if proc.returncode == 0:
                    return stdout_str if stdout_str else "Execution complete. No output."
                else:
                    return f"Execution Error (Exit {proc.returncode}):\n{stderr_str}\n{stdout_str}"
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                return "Execution Error: Run timed out after 8.0 seconds."
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    except Exception as e:
        return f"Error executing Python code: {str(e)}"


class AgentRunner:
    def __init__(self):
        # Action patterns
        # Matches: Action: tool_name {"key": "value"}
        self.action_regex = re.compile(r"Action:\s*(\w+)\s*(\{.*\})", re.DOTALL)
        # Matches XML style: <tool_call name="tool_name">{"key": "value"}</tool_call>
        self.xml_regex = re.compile(r'<tool_call\s+name="(\w+)"\s*>(.*?)</tool_call>', re.DOTALL)

    def _format_tools_prompt(self, tools: List[Tool]) -> str:
        """Construct the ReAct system block containing tool details."""
        prompt = "\n\nYou have access to the following tools:\n"
        
        # Prepend default python sandbox tool
        prompt += "- Tool Name: python_sandbox\n"
        prompt += "  Description: Run any python code in a sandbox. Always print variables you want to inspect.\n"
        prompt += "  Parameters Schema: {\"type\": \"object\", \"properties\": {\"code\": {\"type\": \"string\", \"description\": \"Python code to execute\"}}, \"required\": [\"code\"]}\n\n"

        for t in tools:
            # Skip python_sandbox if already in DB to prevent duplicates
            if t.name == "python_sandbox":
                continue
            prompt += f"- Tool Name: {t.name}\n"
            prompt += f"  Description: {t.description}\n"
            prompt += f"  Parameters Schema: {t.schema_json}\n\n"

        prompt += """
To use a tool, you MUST use the following format:
Thought: [reasoning about what to do next]
Action: [tool_name] {"param1": "val1", ...}

When you have the final answer for the user or if you do not need any tools, use this format:
Final Answer: [your response text]
"""
        return prompt

    async def execute_react_loop(
        self,
        agent: Agent,
        conversation_history: List[Dict[str, str]],
        session: Session
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the Reasoning-Action-Observation loop with the LLM."""
        # Fetch other enabled tools from DB
        stmt = select(Tool)
        tools = session.exec(stmt).all()
        
        tools_prompt = self._format_tools_prompt(tools)
        system_content = f"{agent.system_prompt}{tools_prompt}"
        
        messages = [{"role": "system", "content": system_content}]
        messages.extend(conversation_history)
        
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Agent '{agent.name}' loop iteration {iteration}...")
            
            response_content = ""
            yield {"type": "status", "content": f"Thinking (Iteration {iteration})..."}
            
            async for chunk in ollama_service.chat_completion_stream(
                model=agent.model_name,
                messages=messages,
                options={"temperature": agent.temperature}
            ):
                if chunk.get("type") == "token":
                    response_content += chunk["content"]
                    yield {"type": "token", "content": chunk["content"]}
                elif chunk.get("type") == "error":
                    yield {"type": "error", "content": chunk["content"]}
                    return

            # Analyze output for actions
            action_match = self.action_regex.search(response_content)
            xml_match = self.xml_regex.search(response_content)
            
            tool_name = None
            tool_args_str = None
            
            if action_match:
                tool_name = action_match.group(1).strip()
                tool_args_str = action_match.group(2).strip()
            elif xml_match:
                tool_name = xml_match.group(1).strip()
                tool_args_str = xml_match.group(2).strip()
                
            if tool_name and tool_args_str:
                yield {"type": "tool_start", "tool_name": tool_name, "arguments": tool_args_str}
                
                try:
                    tool_args = json.loads(tool_args_str)
                except json.JSONDecodeError:
                    observation = "Error: Invalid JSON arguments format."
                    yield {"type": "tool_end", "tool_name": tool_name, "status": "error", "result": observation}
                    messages.append({"role": "assistant", "content": response_content})
                    messages.append({"role": "user", "content": f"Observation: {observation}"})
                    continue
                
                # Check for python_sandbox tool natively
                if tool_name == "python_sandbox":
                    code = tool_args.get("code", "")
                    if not code:
                        observation = "Error: Parameter 'code' was empty."
                    else:
                        observation = await execute_python_sandbox(code)
                else:
                    # Retrieve matching tool client from database
                    mcp_client = await mcp_manager.get_tool_client(tool_name, session)
                    if mcp_client:
                        tool_result = await mcp_client.call_tool(tool_name, tool_args)
                        
                        observation = ""
                        content_blocks = tool_result.get("content", [])
                        for block in content_blocks:
                            if block.get("type") == "text":
                                observation += block.get("text", "")
                        
                        if not observation:
                            observation = json.dumps(tool_result)
                    else:
                        observation = f"Error: Tool '{tool_name}' is not currently active."
                
                yield {"type": "tool_end", "tool_name": tool_name, "status": "success", "result": observation}
                
                messages.append({"role": "assistant", "content": response_content})
                messages.append({"role": "user", "content": f"Observation: {observation}"})
            else:
                final_answer = response_content
                if "Final Answer:" in final_answer:
                    final_answer = final_answer.split("Final Answer:")[-1].strip()
                
                yield {"type": "final_answer", "content": final_answer}
                break
                
        if iteration >= max_iterations:
            yield {"type": "final_answer", "content": "Reached max iteration limit without final answer."}

agent_runner = AgentRunner()
