"""Persistent Maestro MCP client for fast UI automation.

Instead of spawning `maestro test` for each operation (14s JVM startup),
this maintains a persistent `maestro mcp` process and sends JSON-RPC calls
over stdio (~250ms per operation).
"""

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Optional
import base64

from ..logging.trace import TraceContext


class MaestroMCPClient:
    """Persistent client for Maestro MCP server.

    Manages a long-running `maestro mcp` subprocess and communicates
    via JSON-RPC over stdio. Auto-starts on first use, reconnects if
    the process dies.
    """

    _instance: Optional["MaestroMCPClient"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self):
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._maestro_path = self._find_maestro()
        self._connected = False
        self._device_id: Optional[str] = None

    @classmethod
    async def get_instance(cls) -> "MaestroMCPClient":
        """Get or create the singleton instance."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = MaestroMCPClient()
            if not cls._instance._connected:
                await cls._instance._ensure_connected()
            return cls._instance

    @classmethod
    async def shutdown(cls):
        """Shutdown the singleton instance."""
        async with cls._lock:
            if cls._instance and cls._instance._process:
                cls._instance._process.terminate()
                try:
                    await asyncio.wait_for(cls._instance._process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    cls._instance._process.kill()
                cls._instance._connected = False
                cls._instance._process = None

    def _find_maestro(self) -> Optional[str]:
        """Find Maestro CLI binary."""
        paths = [
            shutil.which("maestro"),
            str(Path.home() / ".maestro" / "bin" / "maestro"),
            "/usr/local/bin/maestro",
        ]
        for path in paths:
            if path and Path(path).exists():
                return path
        return None

    def is_available(self) -> bool:
        """Check if Maestro is installed."""
        return self._maestro_path is not None

    async def _ensure_connected(self) -> bool:
        """Ensure the maestro mcp process is running."""
        if self._process is not None and self._process.returncode is None:
            self._connected = True
            return True

        if not self._maestro_path:
            return False

        try:
            self._process = await asyncio.create_subprocess_exec(
                self._maestro_path, "mcp",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._connected = True
            self._device_id = None  # Reset device ID on reconnect
            return True
        except Exception as e:
            self._connected = False
            return False

    async def _read_line(self, timeout: float) -> bytes:
        """Read a newline-delimited line, handling large responses (>64KB).

        asyncio's readline() has a 64KB default limit. Screenshot responses
        can be 130KB+, so we read in chunks until we find a newline.
        """
        chunks = []
        chunk_size = 64 * 1024  # 64KB chunks

        async def read_until_newline():
            while True:
                chunk = await self._process.stdout.read(chunk_size)
                if not chunk:
                    return b"".join(chunks) if chunks else b""

                # Check if chunk contains newline
                newline_pos = chunk.find(b"\n")
                if newline_pos >= 0:
                    # Include everything up to and including newline
                    chunks.append(chunk[:newline_pos + 1])
                    return b"".join(chunks)
                else:
                    chunks.append(chunk)

        return await asyncio.wait_for(read_until_newline(), timeout=timeout)

    async def _call(self, method: str, params: dict, timeout: float = 30) -> dict:
        """Send a JSON-RPC call to maestro mcp."""
        if not await self._ensure_connected():
            return {"error": "Maestro MCP not available"}

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._request_id
        }

        request_line = json.dumps(request) + "\n"

        try:
            self._process.stdin.write(request_line.encode())
            await self._process.stdin.drain()

            # Read response - MCP uses newline-delimited JSON
            # Use custom reader to handle large responses (screenshots can be 130KB+)
            response_line = await self._read_line(timeout)

            if not response_line:
                self._connected = False
                return {"error": "Maestro MCP process died"}

            return json.loads(response_line.decode())

        except asyncio.TimeoutError:
            return {"error": f"Timeout after {timeout}s"}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response: {e}"}
        except Exception as e:
            self._connected = False
            return {"error": str(e)}

    async def call_tool(self, name: str, arguments: dict, timeout: float = 30) -> dict:
        """Call a Maestro MCP tool."""
        response = await self._call(
            "tools/call",
            {"name": name, "arguments": arguments},
            timeout=timeout
        )

        if "error" in response:
            return {"success": False, "error": response.get("error")}

        result = response.get("result", {})
        content = result.get("content", [])

        # Extract text content
        text_content = ""
        image_data = None
        for item in content:
            if item.get("type") == "text":
                text_content += item.get("text", "")
            elif item.get("type") == "image":
                image_data = item.get("data")

        # Check for error in content
        if result.get("isError"):
            return {"success": False, "error": text_content}

        return {
            "success": True,
            "content": text_content,
            "image_data": image_data
        }

    async def get_device_id(self, trace: TraceContext, prefer_platform: str = "android") -> Optional[str]:
        """Get a connected device ID, caching the result."""
        if self._device_id:
            return self._device_id

        result = await self.call_tool("list_devices", {})
        if not result.get("success"):
            trace.log("MAESTRO_MCP", f"list_devices failed: {result.get('error')}")
            return None

        content = result.get("content", "")
        trace.log("MAESTRO_MCP", f"list_devices: {content[:200]}")

        # Parse device list - look for connected devices
        try:
            # Content is JSON with devices array
            data = json.loads(content) if content.startswith("{") else {"devices": []}
            devices = data.get("devices", [])

            # Prefer the specified platform
            for device in devices:
                if device.get("connected") and device.get("platform") == prefer_platform:
                    self._device_id = device.get("device_id")
                    trace.log("MAESTRO_MCP", f"Using device: {self._device_id}")
                    return self._device_id

            # Fall back to any connected device
            for device in devices:
                if device.get("connected"):
                    self._device_id = device.get("device_id")
                    trace.log("MAESTRO_MCP", f"Using device: {self._device_id}")
                    return self._device_id
        except json.JSONDecodeError:
            # Try line-based parsing as fallback
            for line in content.split("\n"):
                if "emulator" in line.lower() or "iphone" in line.lower():
                    parts = line.split()
                    if parts:
                        self._device_id = parts[0]
                        return self._device_id

        return None

    async def tap(
        self,
        finder: dict,
        trace: TraceContext,
        timeout: int = 30,
        device: Optional[str] = None,
        app_id: str = "com.example.flutter_control_test_app"
    ) -> dict:
        """Tap on an element using run_flow (more reliable than tap_on tool)."""
        device_id = device or await self.get_device_id(trace)
        if not device_id:
            return {"success": False, "error": "No device connected"}

        # Build flow YAML - use run_flow instead of tap_on tool
        # tap_on tool seems to return success without actually performing the tap
        if "text" in finder:
            # Use regex for partial matching (consistent with legacy mode)
            text = finder["text"]
            flow_yaml = f"appId: {app_id}\n---\n- tapOn: \".*{text}.*\""
        elif "id" in finder:
            flow_yaml = f"appId: {app_id}\n---\n- tapOn:\n    id: \"{finder['id']}\""
        else:
            return {"success": False, "error": f"Unsupported finder: {finder}"}

        trace.log("MAESTRO_MCP", f"tap via run_flow: {finder}")
        result = await self.run_flow(flow_yaml, trace, timeout, device_id)
        trace.log("MAESTRO_MCP", f"tap result: {result.get('success')}")
        return result

    async def enter_text(
        self,
        text: str,
        finder: Optional[dict],
        trace: TraceContext,
        timeout: int = 30,
        device: Optional[str] = None
    ) -> dict:
        """Enter text, optionally tapping an element first."""
        device_id = device or await self.get_device_id(trace)
        if not device_id:
            return {"success": False, "error": "No device connected"}

        # If finder provided, tap on it first
        if finder:
            tap_result = await self.tap(finder, trace, timeout, device_id)
            if not tap_result.get("success"):
                return tap_result

        args = {"device_id": device_id, "text": text}
        trace.log("MAESTRO_MCP", f"input_text: {len(text)} chars")
        result = await self.call_tool("input_text", args, timeout=timeout)
        trace.log("MAESTRO_MCP", f"input_text result: {result.get('success')}")
        return result

    async def screenshot(
        self,
        trace: TraceContext,
        timeout: int = 30,
        device: Optional[str] = None
    ) -> dict:
        """Take a screenshot."""
        device_id = device or await self.get_device_id(trace)
        if not device_id:
            return {"success": False, "error": "No device connected"}

        args = {"device_id": device_id}
        trace.log("MAESTRO_MCP", "take_screenshot")
        result = await self.call_tool("take_screenshot", args, timeout=timeout)

        if result.get("success") and result.get("image_data"):
            result["screenshot_base64"] = result["image_data"]

        trace.log("MAESTRO_MCP", f"screenshot result: {result.get('success')}")
        return result

    async def run_flow(
        self,
        flow_yaml: str,
        trace: TraceContext,
        timeout: int = 30,
        device: Optional[str] = None
    ) -> dict:
        """Run a Maestro flow (for operations not directly supported)."""
        device_id = device or await self.get_device_id(trace)
        if not device_id:
            return {"success": False, "error": "No device connected"}

        args = {"device_id": device_id, "flow_yaml": flow_yaml}
        trace.log("MAESTRO_MCP", f"run_flow: {len(flow_yaml)} chars")
        result = await self.call_tool("run_flow", args, timeout=timeout)
        trace.log("MAESTRO_MCP", f"run_flow result: {result.get('success')}")
        return result

    async def inspect_hierarchy(
        self,
        trace: TraceContext,
        timeout: int = 30,
        device: Optional[str] = None
    ) -> dict:
        """Get the view hierarchy."""
        device_id = device or await self.get_device_id(trace)
        if not device_id:
            return {"success": False, "error": "No device connected"}

        args = {"device_id": device_id}
        trace.log("MAESTRO_MCP", "inspect_view_hierarchy")
        result = await self.call_tool("inspect_view_hierarchy", args, timeout=timeout)
        trace.log("MAESTRO_MCP", f"hierarchy result: {result.get('success')}")
        return result
