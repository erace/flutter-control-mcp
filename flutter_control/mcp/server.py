"""FastAPI MCP server for Flutter Control."""

import asyncio
import json
import os
import platform
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Request, Response
from pydantic import BaseModel

from ..config import TOKEN, MCP_PORT, MCP_HOST, LOG_DIR
from .tools import TOOLS, handle_tool_call
from ..__version__ import __version__ as VERSION
START_TIME = datetime.now(timezone.utc)

# Detect platform based on port
# 9225 = Android (Host), 9226 = iOS (VM), 9227 = iOS (Host)
def _get_platform():
    port = int(os.environ.get("FLUTTER_CONTROL_PORT", MCP_PORT))
    return "ios" if port in (9226, 9227) else "android"

def _get_deployed_at():
    """Get deployment time from server.py mtime."""
    try:
        server_file = Path(__file__)
        mtime = server_file.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
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
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
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


@app.post("/upload-app")
async def upload_app(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_bundle_id: Optional[str] = Header(None, alias="X-Bundle-Id"),
    x_device: Optional[str] = Header(None, alias="X-Device"),
    x_launch: Optional[str] = Header(None, alias="X-Launch"),
):
    """
    Upload and install an app.

    For iOS: Send a zip file containing the .app bundle
    For Android: Send the .apk file directly

    Headers:
        Authorization: Bearer <token>
        X-Bundle-Id: com.example.app (optional, for launching after install)
        X-Device: device ID (optional, defaults to booted/first device)
        X-Launch: true/false (optional, launch after install)
    """
    if not verify_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Read request body
    body = await request.body()
    if len(body) < 100:
        raise HTTPException(status_code=400, detail="App file too small or empty")

    platform_name = _get_platform()
    device = x_device or ("booted" if platform_name == "ios" else None)
    should_launch = x_launch and x_launch.lower() == "true"

    # Create temp directory for extraction
    app_dir = LOG_DIR / "apps"
    app_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    temp_dir = app_dir / f"upload_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        if platform_name == "ios":
            result = await _install_ios_app(body, temp_dir, device, should_launch, x_bundle_id)
        else:
            result = await _install_android_app(body, temp_dir, device, should_launch, x_bundle_id)

        return result
    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _install_ios_app(
    zip_data: bytes,
    temp_dir: Path,
    device: str,
    launch: bool,
    bundle_id: Optional[str],
) -> Dict[str, Any]:
    """Install iOS app from zip data."""
    # Save and extract zip
    zip_path = temp_dir / "app.zip"
    zip_path.write_bytes(zip_data)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(temp_dir)

    # Find .app bundle
    app_bundle = None
    for item in temp_dir.iterdir():
        if item.suffix == ".app" and item.is_dir():
            app_bundle = item
            break

    if not app_bundle:
        # Check one level deeper
        for subdir in temp_dir.iterdir():
            if subdir.is_dir():
                for item in subdir.iterdir():
                    if item.suffix == ".app" and item.is_dir():
                        app_bundle = item
                        break

    if not app_bundle:
        raise ValueError("No .app bundle found in zip")

    # Install via simctl
    process = await asyncio.create_subprocess_exec(
        "xcrun", "simctl", "install", device, str(app_bundle),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)

    if process.returncode != 0:
        error = stderr.decode("utf-8", errors="replace")
        raise ValueError(f"simctl install failed: {error}")

    result = {
        "success": True,
        "platform": "ios",
        "device": device,
        "app_path": str(app_bundle),
        "launched": False,
    }

    # Optionally launch
    if launch and bundle_id:
        launch_process = await asyncio.create_subprocess_exec(
            "xcrun", "simctl", "launch", device, bundle_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(launch_process.communicate(), timeout=30)
        result["launched"] = launch_process.returncode == 0
        result["bundle_id"] = bundle_id

    return result


async def _install_android_app(
    apk_data: bytes,
    temp_dir: Path,
    device: Optional[str],
    launch: bool,
    bundle_id: Optional[str],
) -> Dict[str, Any]:
    """Install Android app from APK data."""
    # Save APK
    apk_path = temp_dir / "app.apk"
    apk_path.write_bytes(apk_data)

    # Find adb
    adb_path = shutil.which("adb")
    if not adb_path:
        # Try common locations
        for path in [
            Path.home() / "Library/Android/sdk/platform-tools/adb",
            Path("/usr/local/bin/adb"),
        ]:
            if path.exists():
                adb_path = str(path)
                break

    if not adb_path:
        raise ValueError("ADB not found")

    # Build command
    cmd = [adb_path]
    if device:
        cmd.extend(["-s", device])
    cmd.extend(["install", "-r", str(apk_path)])

    # Install via adb
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)

    if process.returncode != 0:
        error = stderr.decode("utf-8", errors="replace")
        raise ValueError(f"adb install failed: {error}")

    result = {
        "success": True,
        "platform": "android",
        "device": device,
        "app_path": str(apk_path),
        "launched": False,
    }

    # Optionally launch
    if launch and bundle_id:
        launch_cmd = [adb_path]
        if device:
            launch_cmd.extend(["-s", device])
        launch_cmd.extend([
            "shell", "am", "start",
            "-n", f"{bundle_id}/.MainActivity"
        ])

        launch_process = await asyncio.create_subprocess_exec(
            *launch_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(launch_process.communicate(), timeout=30)
        result["launched"] = launch_process.returncode == 0
        result["bundle_id"] = bundle_id

    return result


def main():
    import uvicorn
    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()
