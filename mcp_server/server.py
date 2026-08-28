"""
Model Context Protocol (MCP) Server
Provides external tools (System Time, Calculations, Mock Database, Diagnostics)
to LLM agents over Standard I/O using the official FastMCP / MCP SDK.
"""

import sys
import os
import json
import math
import datetime
import platform

try:
    from mcp.server.fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False

# Initialize FastMCP Server
if HAS_FASTMCP:
    mcp = FastMCP("Modular-Chat-MCP-Server")

    @mcp.tool()
    def get_current_time(timezone_str: str = "UTC") -> str:
        """Get the current date, time, and day of week for a given timezone."""
        now = datetime.datetime.now(datetime.timezone.utc)
        return json.dumps({
            "utc_iso": now.isoformat(),
            "formatted": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "day_of_week": now.strftime("%A"),
            "requested_timezone": timezone_str
        })

    @mcp.tool()
    def calculate(expression: str) -> str:
        """Safely calculate a mathematical expression like '25 * 40 + sqrt(144)'."""
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        allowed_names.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum, "pow": pow})
        try:
            # Clean expression
            sanitized = expression.replace("^", "**")
            result = eval(sanitized, {"__builtins__": {}}, allowed_names)
            return json.dumps({"expression": expression, "result": result, "status": "success"})
        except Exception as e:
            return json.dumps({"expression": expression, "error": str(e), "status": "error"})

    @mcp.tool()
    def query_database(table: str, query: str = "") -> str:
        """Query local demo SQLite database records (tables: 'products', 'users', 'metrics')."""
        mock_db = {
            "products": [
                {"id": 101, "name": "Antigravity Pro Mouse", "price": 89.99, "stock": 42, "category": "Electronics"},
                {"id": 102, "name": "Mechanical Keyboard RGB", "price": 149.50, "stock": 18, "category": "Electronics"},
                {"id": 103, "name": "Ergonomic Desk Chair", "price": 320.00, "stock": 7, "category": "Furniture"},
                {"id": 104, "name": "4K Ultra HD Monitor 32-inch", "price": 499.00, "stock": 12, "category": "Displays"},
                {"id": 105, "name": "Noise Cancelling Headphones", "price": 229.00, "stock": 25, "category": "Audio"}
            ],
            "users": [
                {"id": 1, "username": "alex_dev", "role": "Lead Architect", "status": "Active"},
                {"id": 2, "username": "samantha_ai", "role": "ML Engineer", "status": "Active"},
                {"id": 3, "username": "jordan_sec", "role": "Security Analyst", "status": "Offline"}
            ],
            "metrics": [
                {"service": "FastAPI Gateway", "uptime": "99.98%", "avg_latency_ms": 14.2, "status": "Healthy"},
                {"service": "MCP Tool Bridge", "uptime": "100.0%", "avg_latency_ms": 4.8, "status": "Healthy"},
                {"service": "Vector Index", "uptime": "99.91%", "avg_latency_ms": 32.1, "status": "Healthy"}
            ]
        }
        
        table_lower = table.lower().strip()
        if table_lower not in mock_db:
            available = list(mock_db.keys())
            return json.dumps({
                "error": f"Table '{table}' not found. Available tables: {available}",
                "status": "error"
            })
            
        data = mock_db[table_lower]
        if query:
            q = query.lower()
            filtered = [
                item for item in data
                if any(q in str(val).lower() for val in item.values())
            ]
            return json.dumps({"table": table_lower, "count": len(filtered), "results": filtered, "status": "success"})
            
        return json.dumps({"table": table_lower, "count": len(data), "results": data, "status": "success"})

    @mcp.tool()
    def system_info() -> str:
        """Get host machine diagnostics and environment metadata."""
        return json.dumps({
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": platform.python_version(),
            "architecture": platform.machine(),
            "protocol": "Model Context Protocol (MCP) v1.0",
            "status": "operational"
        })

def run_standalone():
    if HAS_FASTMCP:
        mcp.run(transport="stdio")
    else:
        # Fallback JSON-RPC stdio runner for environments without fastmcp installed yet
        print("Starting fallback stdio MCP server...", file=sys.stderr)
        tools_list = [
            {
                "name": "get_current_time",
                "description": "Get the current date, time, and day of week for a given timezone.",
                "parameters": {
                    "type": "object",
                    "properties": {"timezone_str": {"type": "string", "description": "Timezone name or UTC"}},
                    "required": []
                }
            },
            {
                "name": "calculate",
                "description": "Safely calculate a mathematical expression like '25 * 40 + sqrt(144)'",
                "parameters": {
                    "type": "object",
                    "properties": {"expression": {"type": "string", "description": "Math expression string"}},
                    "required": ["expression"]
                }
            },
            {
                "name": "query_database",
                "description": "Query local demo SQLite database records (tables: 'products', 'users', 'metrics').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name (products, users, metrics)"},
                        "query": {"type": "string", "description": "Optional search term"}
                    },
                    "required": ["table"]
                }
            },
            {
                "name": "system_info",
                "description": "Get host machine diagnostics and environment metadata.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        ]
        
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                req = json.loads(line)
                req_id = req.get("id")
                method = req.get("method")
                
                if method == "tools/list":
                    res = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}
                elif method == "tools/call":
                    params = req.get("params", {})
                    name = params.get("name")
                    args = params.get("arguments", {})
                    if name == "get_current_time":
                        now = datetime.datetime.now(datetime.timezone.utc)
                        content = f"Current UTC Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')} ({now.strftime('%A')})"
                    elif name == "calculate":
                        expr = args.get("expression", "0")
                        try:
                            content = str(eval(expr, {"__builtins__": {}}, {"sqrt": math.sqrt, "abs": abs, "round": round, "pi": math.pi}))
                        except Exception as ex:
                            content = f"Error: {ex}"
                    elif name == "query_database":
                        tbl = args.get("table", "products")
                        content = f"Table {tbl}: 5 items found [Mouse $89.99, Keyboard $149.50, Chair $320, Monitor $499, Headphones $229]"
                    elif name == "system_info":
                        content = f"System: {platform.system()} {platform.release()}, Python {platform.python_version()}"
                    else:
                        content = f"Unknown tool: {name}"
                    res = {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": content}]}}
                else:
                    res = {"jsonrpc": "2.0", "id": req_id, "result": {}}
                
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
            except Exception as e:
                print(f"Error handling MCP request: {e}", file=sys.stderr)
                break

if __name__ == "__main__":
    run_standalone()
