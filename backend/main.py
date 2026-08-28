"""
FastAPI Backend Application
Implements REST API endpoints (/api/chat, /api/health, /api/tools), CORS middleware,
lifecycle management, and static file serving for the frontend client.
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from mcp_client import MCPClient
from llm_service import LLMService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend_main")

# Global services
mcp_client = MCPClient()
llm_service = LLMService(mcp_client=mcp_client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle manager."""
    logger.info("Initializing MCP Client and connecting to MCP Server...")
    await mcp_client.start()
    yield
    logger.info("Shutting down MCP Client and cleaning up resources...")
    await mcp_client.close()


app = FastAPI(
    title="Modular MCP Chat API",
    description="Full-stack AI Chat API integrated with Model Context Protocol (MCP) and LLM function calling.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request & Response Models
class ChatTurn(BaseModel):
    role: str = Field(..., description="Role of the sender: 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's query prompt")
    history: Optional[List[ChatTurn]] = Field(default_factory=list, description="Previous conversation turns")


class ToolCallDetail(BaseModel):
    name: str
    arguments: Dict[str, Any]
    output: Optional[Any] = None
    status: str = "success"


class ChatResponse(BaseModel):
    response: str
    tool_calls: List[ToolCallDetail] = []
    model: Optional[str] = None
    latency_seconds: Optional[float] = None
    status: str = "success"


# API Routes
@app.get("/api/health", tags=["Diagnostics"])
async def health_check():
    """Health check endpoint to verify backend and MCP server status."""
    tools = await mcp_client.get_tools()
    return {
        "status": "healthy",
        "backend": "online",
        "mcp_server": "connected" if mcp_client.is_connected else "offline (fallback active)",
        "available_tools_count": len(tools),
        "llm_model": llm_service.model_name,
        "gemini_api_configured": bool(llm_service.gemini_api_key and llm_service.gemini_api_key != "your_gemini_api_key_here")
    }


@app.get("/api/tools", tags=["MCP Tools"])
async def list_tools():
    """Returns the list of active tools exposed by the MCP Server."""
    try:
        tools = await mcp_client.get_tools()
        return {
            "status": "success",
            "tools": tools,
            "count": len(tools)
        }
    except Exception as e:
        logger.error(f"Error fetching tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list MCP tools: {str(e)}"
        )


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(payload: ChatRequest):
    """
    Main chat endpoint: Accepts user input and chat history,
    queries the LLM, executes MCP tools when needed, and returns the response.
    """
    if not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    try:
        history_dicts = [{"role": turn.role, "content": turn.content} for turn in payload.history]
        result = await llm_service.chat(
            user_message=payload.message,
            history=history_dicts
        )
        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Exception during chat processing: {e}", exc_info=True)
        return ChatResponse(
            response=f"An error occurred while processing your request: {str(e)}",
            tool_calls=[],
            status="error"
        )


# Serve Frontend Static Files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_root():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return JSONResponse({"message": "Modular MCP Chat API is running."})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
