"""FastAPI MCP server for Flutter Control."""

import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from ..config import TOKEN, MCP_PORT, MCP_HOST
from .tools import TOOLS, handle_tool_call

VERSION = "1.0.0"
START_TIME = datetime.utcnow()

# Detect platform based on port
def _get_platform():
    port = int(os.environ.get("FLUTTER_CONTROL_PORT", MCP_PORT))
    return "ios" if port == 9226 else "android"

def _get_deployed_at():
    """Get deployment time from server.py mtime."""
    try:
        server_file = Path(__file__)
        mtime = server_file.stat().st_mtime
        return datetime.utcfromtimestamp(mtime).isoformat() + "Z"
    except:
        return None

def _get_git_commit():
    """Get git commit if available."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None

app = FastAPI(title="Flutter Control MCP Server")


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = {}


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Optional[Dict[str, Any]] = None


def verify_token(authorization: Optional[str]) -> bool:
    if not TOKEN:
        return True
    if not authorization:
        return False
    if not authorization.startswith("Bearer "):
        return False
    return authorization[7:] == TOKEN


@app.get("/health")
async def health():
    return {"status": "ok", "service": "flutter-control"}


@app.get("/version")
async def version():
    """Get service version and deployment info."""
    uptime = (datetime.utcnow() - START_TIME).total_seconds()
    return {
        "service": "flutter-control",
        "platform": _get_platform(),
        "version": VERSION,
        "deployed_at": _get_deployed_at(),
        "git_commit": _get_git_commit(),
        "started_at": START_TIME.isoformat() + "Z",
        "uptime_seconds": int(uptime),
        "hostname": platform.node(),
    }


@app.get("/tools")
async def list_tools(authorization: Optional[str] = Header(None)):
    if not verify_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"tools": TOOLS}


@app.post("/call")
async def call_tool(request: ToolCallRequest, authorization: Optional[str] = Header(None)):
    if not verify_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await handle_tool_call(request.name, request.arguments)


@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest, authorization: Optional[str] = Header(None)):
    if not verify_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if request.method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "flutter-control", "version": "0.1.0"},
            },
        }
    elif request.method == "tools/list":
        return {"jsonrpc": "2.0", "id": request.id, "result": {"tools": TOOLS}}
    elif request.method == "tools/call":
        params = request.params or {}
        result = await handle_tool_call(params.get("name", ""), params.get("arguments", {}))
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "isError": not result.get("success", False),
            },
        }
    else:
        return {"jsonrpc": "2.0", "id": request.id, "error": {"code": -32601, "message": f"Method not found: {request.method}"}}


def main():
    import uvicorn
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()
