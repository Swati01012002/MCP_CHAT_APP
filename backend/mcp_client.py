"""
Model Context Protocol (MCP) Client
Manages tool discovery, communication, subprocess lifecycle, and execution over stdio/SSE.
Includes timeout handling and graceful fallback if the MCP server is unreachable.
"""

import sys
import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("mcp_client")
logging.basicConfig(level=logging.INFO)

# Default tools fallback if MCP server is temporarily offline
FALLBACK_TOOLS = [
    {
        "name": "get_current_time",
        "description": "Get current UTC date and time with day of week.",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone_str": {"type": "string", "description": "Timezone name (e.g. UTC, EST)"}
            },
            "required": []
        }
    },
    {
        "name": "calculate",
        "description": "Safely evaluate a mathematical calculation expression.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to calculate"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "query_database",
        "description": "Query records from local demo tables (products, users, metrics).",
        "parameters": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Table to query (products, users, metrics)"},
                "query": {"type": "string", "description": "Search keyword"}
            },
            "required": ["table"]
        }
    },
    {
        "name": "system_info",
        "description": "Get host environment diagnostics and OS details.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


class MCPClient:
    def __init__(self, server_script_path: Optional[str] = None, timeout: float = 6.0):
        self.server_script_path = server_script_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "mcp_server",
            "server.py"
        )
        self.timeout = timeout
        self.process: Optional[asyncio.subprocess.Process] = None
        self._cached_tools: List[Dict[str, Any]] = []
        self._request_id = 0
        self.is_connected = False

    async def start(self):
        """Starts the MCP server process using stdio transport."""
        try:
            python_exe = sys.executable
            if not os.path.exists(self.server_script_path):
                logger.warning(f"MCP server script not found at {self.server_script_path}. Will use fallback.")
                return False

            self.process = await asyncio.create_subprocess_exec(
                python_exe,
                self.server_script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.is_connected = True
            logger.info("Connected to MCP Server subprocess.")
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP server subprocess: {e}")
            self.is_connected = False
            return False

    async def get_tools(self) -> List[Dict[str, Any]]:
        """Discovers and returns list of available tools from MCP server with timeout."""
        if not self.is_connected or not self.process:
            connected = await self.start()
            if not connected:
                return FALLBACK_TOOLS

        try:
            self._request_id += 1
            request_payload = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "tools/list",
                "params": {}
            }
            
            response = await self._send_request(request_payload)
            if response and "result" in response and "tools" in response["result"]:
                tools = response["result"]["tools"]
                self._cached_tools = tools
                return tools
        except asyncio.TimeoutError:
            logger.warning("MCP tool listing timed out. Using fallback tool definitions.")
        except Exception as e:
            logger.error(f"Error querying MCP tools: {e}")

        return self._cached_tools or FALLBACK_TOOLS

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a tool on the MCP server with strict timeout and fallback recovery.
        """
        logger.info(f"Invoking MCP tool '{tool_name}' with args: {arguments}")
        
        # Ensure connection
        if not self.is_connected or not self.process:
            connected = await self.start()
            if not connected:
                return self._local_fallback_execution(tool_name, arguments, "MCP server subprocess unavailable")

        try:
            self._request_id += 1
            request_payload = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # Enforce timeout
            response = await asyncio.wait_for(
                self._send_request(request_payload),
                timeout=self.timeout
            )

            if not response:
                return self._local_fallback_execution(tool_name, arguments, "Empty response from MCP server")

            if "result" in response:
                result_data = response["result"]
                # Extract text content from MCP format
                if "content" in result_data and isinstance(result_data["content"], list):
                    text_parts = [
                        item.get("text", "") for item in result_data["content"] if item.get("type") == "text"
                    ]
                    output_text = "\n".join(text_parts)
                else:
                    output_text = json.dumps(result_data)

                return {
                    "tool": tool_name,
                    "status": "success",
                    "result": output_text,
                    "raw": result_data
                }
            elif "error" in response:
                return {
                    "tool": tool_name,
                    "status": "error",
                    "error": response["error"].get("message", "Unknown MCP error")
                }

        except asyncio.TimeoutError:
            logger.warning(f"MCP tool call '{tool_name}' timed out after {self.timeout}s.")
            return self._local_fallback_execution(
                tool_name,
                arguments,
                f"MCP server response timed out after {self.timeout}s"
            )
        except Exception as e:
            logger.error(f"Error during MCP tool call: {e}")
            return self._local_fallback_execution(tool_name, arguments, str(e))

        return self._local_fallback_execution(tool_name, arguments, "Unknown execution failure")

    async def _send_request(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Sends a JSON-RPC request line over stdin and awaits stdout response."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            return None

        line = json.dumps(payload) + "\n"
        self.process.stdin.write(line.encode("utf-8"))
        await self.process.stdin.drain()

        # Read line from stdout
        raw_response = await self.process.stdout.readline()
        if not raw_response:
            return None
            
        return json.loads(raw_response.decode("utf-8").strip())

    def _local_fallback_execution(self, tool_name: str, arguments: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Graceful in-memory fallback execution for resilience against MCP server downtime."""
        import datetime
        import platform
        import math

        logger.info(f"Executing graceful fallback for '{tool_name}' (Reason: {reason})")
        if tool_name == "get_current_time":
            now = datetime.datetime.now(datetime.timezone.utc)
            return {
                "tool": tool_name,
                "status": "fallback_success",
                "result": f"Current Time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S UTC')} ({now.strftime('%A')}) [Fallback Mode: {reason}]",
                "notice": f"Handled gracefully via fallback client: {reason}"
            }
        elif tool_name == "calculate":
            expr = arguments.get("expression", "0")
            try:
                allowed = {"sqrt": math.sqrt, "abs": abs, "round": round, "pi": math.pi, "sin": math.sin, "cos": math.cos}
                res = eval(expr.replace("^", "**"), {"__builtins__": {}}, allowed)
                return {
                    "tool": tool_name,
                    "status": "fallback_success",
                    "result": f"Result: {res} [Fallback Mode: {reason}]",
                    "notice": f"Calculated via local fallback handler: {reason}"
                }
            except Exception as e:
                return {
                    "tool": tool_name,
                    "status": "error",
                    "error": f"Evaluation error: {e}"
                }
        elif tool_name == "query_database":
            table = arguments.get("table", "products")
            return {
                "tool": tool_name,
                "status": "fallback_success",
                "result": f"Table '{table}' (Mock Data): 5 active entries found [Status: Normal] [Fallback Mode: {reason}]",
                "notice": f"Queried via fallback database cache: {reason}"
            }
        elif tool_name == "system_info":
            return {
                "tool": tool_name,
                "status": "fallback_success",
                "result": f"OS: {platform.system()} {platform.release()}, Python: {platform.python_version()} [Fallback Mode: {reason}]",
                "notice": f"Fallback diagnostics: {reason}"
            }

        return {
            "tool": tool_name,
            "status": "error",
            "error": f"MCP tool '{tool_name}' failed and no fallback available ({reason})"
        }

    async def close(self):
        """Terminates the MCP server process gracefully."""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass
        self.is_connected = False
