"""Flutter Driver client - connects to Observatory via WebSocket."""

import asyncio
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    websockets = None  # type: ignore
    WebSocketClientProtocol = None  # type: ignore

from .protocol import DriverProtocol, DriverRequest, DriverResponse, Commands
from .finders import Finder
from ..logging.trace import TraceContext


@dataclass
class IsolateInfo:
    """Information about a Flutter isolate."""

    id: str
    name: str
    number: str


class FlutterDriverClient:
    """Client for Flutter Driver protocol over Observatory WebSocket."""

    def __init__(self, host: str = "localhost", port: int = 9223, uri: Optional[str] = None):
        if websockets is None:
            raise ImportError("websockets package required: pip install websockets")
        self.host = host
        self.port = port
        self._uri = uri  # Full VM service URI if provided
        self.ws: Optional[WebSocketClientProtocol] = None
        self.protocol = DriverProtocol()
        self.isolate_id: Optional[str] = None
        self._pending: Dict[str, asyncio.Future] = {}
        self._receive_task: Optional[asyncio.Task] = None

    @property
    def ws_url(self) -> str:
        """WebSocket URL for Observatory."""
        if self._uri:
            # Convert http://host:port/path/ to ws://host:port/path/ws
            uri = self._uri.replace("http://", "ws://").replace("https://", "wss://")
            if uri.endswith("/"):
                return uri + "ws"
            return uri + "/ws"
        return f"ws://{self.host}:{self.port}/ws"

    async def connect(self, trace: Optional[TraceContext] = None) -> bool:
        """Connect to Observatory and find Flutter isolate."""
        if trace:
            trace.log("DRIVER_CONNECT", f"Connecting to {self.ws_url}")

        try:
            self.ws = await asyncio.wait_for(
                websockets.connect(self.ws_url),
                timeout=10,
            )
            if trace:
                trace.log("DRIVER_WS", "WebSocket connected")

            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())

            # Get VM info and find isolate
            vm_info = await self._send_request("getVM")
            if not vm_info.success:
                if trace:
                    trace.log("DRIVER_ERR", f"getVM failed: {vm_info.error}")
                return False

            isolates = vm_info.response.get("isolates", [])
            if not isolates:
                if trace:
                    trace.log("DRIVER_ERR", "No isolates found")
                return False

            # Find main isolate (usually has "main" in name)
            for iso in isolates:
                iso_id = iso.get("id")
                iso_name = iso.get("name", "")
                if "main" in iso_name.lower() or len(isolates) == 1:
                    self.isolate_id = iso_id
                    if trace:
                        trace.log("DRIVER_ISOLATE", f"Using isolate: {iso_name} ({iso_id})")
                    break

            if not self.isolate_id:
                # Fall back to first isolate
                self.isolate_id = isolates[0].get("id")
                if trace:
                    trace.log("DRIVER_ISOLATE", f"Using first isolate: {self.isolate_id}")

            # Verify driver extension is available
            if not await self._check_driver_extension(trace):
                if trace:
                    trace.log("DRIVER_ERR", "Flutter Driver extension not enabled")
                return False

            if trace:
                trace.log("DRIVER_READY", "Connected and ready")
            return True

        except asyncio.TimeoutError:
            if trace:
                trace.log("DRIVER_ERR", "Connection timeout")
            return False
        except Exception as e:
            if trace:
                trace.log("DRIVER_ERR", f"Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Observatory."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self.ws:
            await self.ws.close()
            self.ws = None
        self.isolate_id = None

    async def _receive_loop(self) -> None:
        """Receive messages from WebSocket."""
        try:
            async for message in self.ws:  # type: ignore
                data = json.loads(message)
                req_id = data.get("id")
                if req_id and req_id in self._pending:
                    self._pending[req_id].set_result(data)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> DriverResponse:
        """Send a VM Service request and wait for response."""
        if not self.ws:
            return DriverResponse(success=False, error="Not connected")

        request = self.protocol.make_vm_service_request(method, params)
        req_id = request["id"]

        future: asyncio.Future = asyncio.Future()
        self._pending[req_id] = future

        try:
            await self.ws.send(json.dumps(request))
            data = await asyncio.wait_for(future, timeout=30)
            return self.protocol.parse_response(data)
        except asyncio.TimeoutError:
            return DriverResponse(success=False, error="Request timeout")
        finally:
            self._pending.pop(req_id, None)

    async def _check_driver_extension(self, trace: Optional[TraceContext] = None) -> bool:
        """Check if Flutter Driver extension is available."""
        if not self.isolate_id:
            return False

        # Get isolate info to check extensions
        resp = await self._send_request("getIsolate", {"isolateId": self.isolate_id})
        if not resp.success:
            return False

        extensions = resp.response.get("extensionRPCs", [])
        has_driver = DriverProtocol.DRIVER_EXTENSION in extensions

        if trace:
            trace.log(
                "DRIVER_EXT",
                f"Driver extension: {'available' if has_driver else 'NOT available'}",
            )

        return has_driver

    async def execute(
        self, command: DriverRequest, trace: Optional[TraceContext] = None
    ) -> DriverResponse:
        """Execute a Flutter Driver command."""
        if not self.ws or not self.isolate_id:
            return DriverResponse(success=False, error="Not connected")

        if trace:
            trace.log("DRIVER_CMD", f"{command.command} {command.params}")

        request = self.protocol.make_driver_request(self.isolate_id, command)
        req_id = request["id"]

        future: asyncio.Future = asyncio.Future()
        self._pending[req_id] = future

        try:
            await self.ws.send(json.dumps(request))
            timeout = command.timeout or 30
            data = await asyncio.wait_for(future, timeout=timeout)
            response = self.protocol.parse_response(data)

            if trace:
                if response.success:
                    trace.log("DRIVER_OK", f"{command.command} succeeded")
                else:
                    trace.log("DRIVER_ERR", f"{command.command} failed: {response.error}")

            return response
        except asyncio.TimeoutError:
            if trace:
                trace.log("DRIVER_ERR", f"{command.command} timeout")
            return DriverResponse(success=False, error="Command timeout")
        finally:
            self._pending.pop(req_id, None)

    # High-level commands

    async def tap(
        self, finder: Finder, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> DriverResponse:
        """Tap on a widget."""
        cmd = DriverRequest(
            command=Commands.TAP,
            params=finder.serialize(),
            timeout=timeout,
        )
        return await self.execute(cmd, trace)

    async def enter_text(
        self, text: str, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> DriverResponse:
        """Enter text into focused field."""
        cmd = DriverRequest(
            command=Commands.ENTER_TEXT,
            params={"text": text},
            timeout=timeout,
        )
        return await self.execute(cmd, trace)

    async def get_text(
        self, finder: Finder, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> DriverResponse:
        """Get text from a widget."""
        cmd = DriverRequest(
            command=Commands.GET_TEXT,
            params=finder.serialize(),
            timeout=timeout,
        )
        return await self.execute(cmd, trace)

    async def scroll_into_view(
        self,
        finder: Finder,
        alignment: float = 0.0,
        trace: Optional[TraceContext] = None,
        timeout: int = 30,
    ) -> DriverResponse:
        """Scroll until widget is visible."""
        cmd = DriverRequest(
            command=Commands.SCROLL_INTO_VIEW,
            params={**finder.serialize(), "alignment": alignment},
            timeout=timeout,
        )
        return await self.execute(cmd, trace)

    async def wait_for(
        self, finder: Finder, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> DriverResponse:
        """Wait for widget to appear."""
        cmd = DriverRequest(
            command=Commands.WAIT_FOR,
            params=finder.serialize(),
            timeout=timeout,
        )
        return await self.execute(cmd, trace)

    async def wait_for_absent(
        self, finder: Finder, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> DriverResponse:
        """Wait for widget to disappear."""
        cmd = DriverRequest(
            command=Commands.WAIT_FOR_ABSENT,
            params=finder.serialize(),
            timeout=timeout,
        )
        return await self.execute(cmd, trace)

    async def get_render_tree(
        self, trace: Optional[TraceContext] = None
    ) -> DriverResponse:
        """Get the render tree."""
        cmd = DriverRequest(command=Commands.GET_RENDER_TREE)
        return await self.execute(cmd, trace)

    async def get_semantics_tree(
        self, trace: Optional[TraceContext] = None
    ) -> DriverResponse:
        """Get the semantics tree."""
        cmd = DriverRequest(command=Commands.GET_SEMANTICS_TREE)
        return await self.execute(cmd, trace)

    async def screenshot(
        self, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> DriverResponse:
        """Take a screenshot (returns base64 PNG)."""
        cmd = DriverRequest(
            command=Commands.SCREENSHOT,
            timeout=timeout,
        )
        return await self.execute(cmd, trace)
