"""MCP tool definitions and handlers."""

import asyncio
import base64
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from ..maestro import MaestroWrapper
from ..logging.trace import TraceContext, generate_trace_id, log_trace, get_recent_traces, get_trace
from ..config import OBSERVATORY_PORT_ANDROID, OBSERVATORY_PORT_IOS

_maestro = MaestroWrapper()

# Flutter Driver client (lazy initialized)
_driver_client = None

# Unified executor (lazy initialized)
_unified_executor = None


def _get_driver_client(port: int = OBSERVATORY_PORT_ANDROID):
    """Get or create Flutter Driver client."""
    global _driver_client
    if _driver_client is None:
        from ..driver import FlutterDriverClient
        _driver_client = FlutterDriverClient(port=port)
    return _driver_client


def _get_unified_executor():
    """Get or create unified executor."""
    global _unified_executor
    if _unified_executor is None:
        from ..unified import UnifiedExecutor
        _unified_executor = UnifiedExecutor(_maestro, _get_driver_client())
    return _unified_executor


async def _ensure_driver_connected(trace: TraceContext, port: int = OBSERVATORY_PORT_ANDROID) -> bool:
    """Ensure driver is connected."""
    client = _get_driver_client(port)
    if client.ws is None:
        return await client.connect(trace)
    return True

def _find_adb() -> Optional[str]:
    """Find ADB binary."""
    paths = [
        shutil.which("adb"),
        str(Path.home() / "Library/Android/sdk/platform-tools/adb"),
        "/usr/local/bin/adb",
    ]
    for path in paths:
        if path and Path(path).exists():
            return path
    return None

_adb_path = _find_adb()


async def _discover_vm_service_uri(trace: TraceContext, device: Optional[str] = None) -> Optional[str]:
    """Discover VM service URI from device logcat."""
    if not _adb_path:
        return None

    cmd = [_adb_path]
    if device:
        cmd.extend(["-s", device])
    cmd.extend(["logcat", "-d"])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)
        output = stdout.decode("utf-8", errors="replace")

        # Find the most recent VM service URI
        for line in reversed(output.split("\n")):
            if "Dart VM service is listening on" in line or "Observatory listening on" in line:
                # Extract URI from line like: "The Dart VM service is listening on http://127.0.0.1:42291/1wQVtz5YTB0=/"
                import re
                match = re.search(r"http://[^\s]+", line)
                if match:
                    uri = match.group(0)
                    trace.log("DISCOVER_URI", uri)
                    return uri
        return None
    except Exception as e:
        trace.log("DISCOVER_ERR", str(e))
        return None


async def _forward_vm_service_port(trace: TraceContext, device_port: int, host_port: int = 9223, device: Optional[str] = None) -> bool:
    """Forward VM service port from device to host."""
    if not _adb_path:
        return False

    cmd = [_adb_path]
    if device:
        cmd.extend(["-s", device])
    cmd.extend(["forward", f"tcp:{host_port}", f"tcp:{device_port}"])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        if process.returncode == 0:
            trace.log("FORWARD_OK", f"localhost:{host_port} -> device:{device_port}")
            return True
        trace.log("FORWARD_ERR", stderr.decode())
        return False
    except Exception as e:
        trace.log("FORWARD_ERR", str(e))
        return False


async def _adb_screenshot(trace: TraceContext, device: Optional[str] = None) -> Dict[str, Any]:
    """Take screenshot using ADB screencap."""
    if not _adb_path:
        return {"success": False, "error": "ADB not found"}

    cmd = [_adb_path]
    if device:
        cmd.extend(["-s", device])
    cmd.extend(["exec-out", "screencap", "-p"])

    trace.log("ADB_CMD", " ".join(cmd))

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)

        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace")
            trace.log("ADB_ERR", error)
            return {"success": False, "error": f"ADB failed: {error}"}

        # stdout is raw PNG data
        if len(stdout) < 100:
            trace.log("ADB_ERR", "Empty or invalid screenshot")
            return {"success": False, "error": "Empty screenshot"}

        image_b64 = base64.b64encode(stdout).decode("utf-8")
        trace.log("ADB_OK", f"{len(stdout)} bytes")

        return {
            "success": True,
            "error": None,
            "image": image_b64,
            "format": "png",
            "encoding": "base64",
        }
    except asyncio.TimeoutError:
        trace.log("ADB_ERR", "Timeout")
        return {"success": False, "error": "ADB timeout"}
    except Exception as e:
        trace.log("ADB_ERR", str(e))
        return {"success": False, "error": str(e)}


async def _flutter_run(
    project_path: str,
    port: int,
    device: Optional[str],
    flavor: Optional[str],
    trace: TraceContext,
    timeout: int,
) -> Dict[str, Any]:
    """Run Flutter app with Observatory enabled."""
    flutter_path = shutil.which("flutter")
    if not flutter_path:
        return {"success": False, "error": "Flutter not found in PATH"}

    project = Path(project_path)
    if not project.exists():
        return {"success": False, "error": f"Project not found: {project_path}"}

    # Build command
    cmd = [
        flutter_path,
        "run",
        "--observatory-port", str(port),
        "--enable-dart-profiling",
    ]
    if device:
        cmd.extend(["-d", device])
    if flavor:
        cmd.extend(["--flavor", flavor])

    trace.log("FLUTTER_RUN", " ".join(cmd))

    try:
        # Start process in background
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project),
        )

        # Wait for Observatory to be ready (look for "Observatory" or "VM Service" in output)
        start_time = asyncio.get_event_loop().time()
        output_lines = []

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                line = await asyncio.wait_for(
                    process.stdout.readline(),  # type: ignore
                    timeout=1.0,
                )
                if line:
                    decoded = line.decode("utf-8", errors="replace").strip()
                    output_lines.append(decoded)
                    trace.log("FLUTTER_OUT", decoded)

                    # Check for Observatory URL
                    if "observatory" in decoded.lower() or "vm service" in decoded.lower():
                        if f":{port}" in decoded or "localhost" in decoded:
                            trace.log("FLUTTER_READY", f"Observatory on port {port}")
                            return {
                                "success": True,
                                "message": f"App running with Observatory on port {port}",
                                "port": port,
                                "pid": process.pid,
                            }

                    # Check for errors
                    if "error" in decoded.lower() and "failed" in decoded.lower():
                        trace.log("FLUTTER_ERR", decoded)
                        process.terminate()
                        return {"success": False, "error": decoded}
            except asyncio.TimeoutError:
                continue

        # Timeout waiting for Observatory
        process.terminate()
        trace.log("FLUTTER_ERR", "Timeout waiting for Observatory")
        return {
            "success": False,
            "error": "Timeout waiting for Observatory to start",
            "output": output_lines[-10:] if output_lines else [],
        }

    except Exception as e:
        trace.log("FLUTTER_ERR", str(e))
        return {"success": False, "error": str(e)}


TOOLS = [
    {
        "name": "flutter_tap",
        "description": "Tap on a UI element. Auto-selects backend: {text:'...'}/{id:'...'} uses Maestro, {key:'...'}/{type:'...'} uses Driver. Falls back automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "finder": {"type": "object", "description": "Element finder: {text:'...'}, {id:'...'}, {key:'...'}, or {type:'...'}"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
                "device": {"type": "string", "description": "Device ID"},
                "backend": {"type": "string", "enum": ["auto", "maestro", "driver"], "description": "Force specific backend (default: auto)"},
            },
            "required": ["finder"],
        },
    },
    {
        "name": "flutter_double_tap",
        "description": "Double tap on a UI element.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "finder": {"type": "object"},
                "timeout": {"type": "integer"},
                "device": {"type": "string"},
            },
            "required": ["finder"],
        },
    },
    {
        "name": "flutter_long_press",
        "description": "Long press on a UI element.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "finder": {"type": "object"},
                "timeout": {"type": "integer"},
                "device": {"type": "string"},
            },
            "required": ["finder"],
        },
    },
    {
        "name": "flutter_swipe",
        "description": "Swipe in a direction.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "timeout": {"type": "integer"},
                "device": {"type": "string"},
            },
            "required": ["direction"],
        },
    },
    {
        "name": "flutter_enter_text",
        "description": "Enter text into a field. If finder provided, taps that element first.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to enter"},
                "finder": {"type": "object", "description": "Optional: element to tap first"},
                "timeout": {"type": "integer"},
                "device": {"type": "string"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "flutter_clear_text",
        "description": "Clear the current text field.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "timeout": {"type": "integer"},
                "device": {"type": "string"},
            },
        },
    },
    {
        "name": "flutter_assert_visible",
        "description": "Assert element is visible. Auto-selects backend with fallback.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "finder": {"type": "object", "description": "Element finder: {text:'...'}, {id:'...'}, {key:'...'}, or {type:'...'}"},
                "timeout": {"type": "integer"},
                "device": {"type": "string"},
                "backend": {"type": "string", "enum": ["auto", "maestro", "driver"], "description": "Force specific backend (default: auto)"},
            },
            "required": ["finder"],
        },
    },
    {
        "name": "flutter_assert_not_visible",
        "description": "Assert that an element is NOT visible on screen.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "finder": {"type": "object"},
                "timeout": {"type": "integer"},
                "device": {"type": "string"},
            },
            "required": ["finder"],
        },
    },
    {
        "name": "flutter_screenshot",
        "description": "Take a screenshot of the current screen (uses Maestro).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "timeout": {"type": "integer"},
                "device": {"type": "string"},
            },
        },
    },
    {
        "name": "flutter_screenshot_adb",
        "description": "Take a screenshot using ADB (faster, no Maestro overhead).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device ID (default: first device)"},
            },
        },
    },
    {
        "name": "flutter_debug_traces",
        "description": "Get recent trace logs for debugging.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of traces (default: 5)"},
            },
        },
    },
    {
        "name": "flutter_debug_trace",
        "description": "Get a specific trace by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trace_id": {"type": "string"},
            },
            "required": ["trace_id"],
        },
    },
    # Phase 2: Flutter Driver tools
    {
        "name": "flutter_get_text",
        "description": "Get text from a widget. Finder: {key: 'widget_key'} or {type: 'Text'}. Requires Flutter Driver extension.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "finder": {"type": "object", "description": "Element finder: {key: '...'}, {type: '...'}, or {text: '...'}"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
                "port": {"type": "integer", "description": "Observatory port (default: 9223 for Android)"},
            },
            "required": ["finder"],
        },
    },
    {
        "name": "flutter_widget_tree",
        "description": "Get the widget/render tree. Requires Flutter Driver extension.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "integer", "description": "Observatory port (default: 9223 for Android)"},
            },
        },
    },
    {
        "name": "flutter_run",
        "description": "Launch Flutter app with Observatory enabled. Returns Observatory port for driver connection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Path to Flutter project"},
                "device": {"type": "string", "description": "Device ID (default: first available)"},
                "flavor": {"type": "string", "description": "Build flavor (optional)"},
                "port": {"type": "integer", "description": "Observatory port (default: 9223)"},
            },
            "required": ["project_path"],
        },
    },
    {
        "name": "flutter_driver_tap",
        "description": "Tap widget via Flutter Driver. Finder: {key: 'widget_key'} or {type: 'ElevatedButton'}. Requires Flutter Driver extension.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "finder": {"type": "object", "description": "Element finder: {key: '...'}, {type: '...'}, or {text: '...'}"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
                "port": {"type": "integer", "description": "Observatory port (default: 9223 for Android)"},
            },
            "required": ["finder"],
        },
    },
    {
        "name": "flutter_driver_connect",
        "description": "Connect to Flutter app's Observatory/VM Service. Must be called before using driver-based tools.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uri": {"type": "string", "description": "Full VM service URI (e.g., http://127.0.0.1:9223/abc123=/). If provided, port/host are ignored."},
                "port": {"type": "integer", "description": "Observatory port (default: 9223 for Android)"},
                "host": {"type": "string", "description": "Observatory host (default: localhost)"},
            },
        },
    },
    {
        "name": "flutter_driver_disconnect",
        "description": "Disconnect from Flutter app's Observatory.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "flutter_driver_discover",
        "description": "Discover VM service URI from device and set up port forwarding. Returns the URI to use with flutter_driver_connect.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device ID (default: first device)"},
                "host_port": {"type": "integer", "description": "Host port for forwarding (default: 9223)"},
            },
        },
    },
    # Phase 6: Version/Health tools
    {
        "name": "flutter_version",
        "description": "Get service version and deployment info. Useful for debugging and verifying the server is up-to-date.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle an MCP tool call."""
    trace_id = generate_trace_id()
    trace = TraceContext(trace_id=trace_id, tool_name=name, arguments=arguments)
    trace.log("MCP_RECV", f"{name} {arguments}")

    try:
        result = await _execute_tool(name, arguments, trace)
        trace.log("MCP_RESP", f"success={result.get('success', False)}")
        log_trace(trace)
        return {**result, "trace_id": trace_id}
    except Exception as e:
        trace.log("MCP_ERR", str(e))
        log_trace(trace)
        return {"success": False, "error": str(e), "trace_id": trace_id}


async def _execute_tool(name: str, arguments: Dict[str, Any], trace: TraceContext) -> Dict[str, Any]:
    """Execute a tool by name."""
    timeout = arguments.get("timeout", 30)
    device = arguments.get("device")

    if name == "flutter_tap":
        backend_arg = arguments.get("backend", "auto")
        finder = arguments["finder"].copy()

        # If explicit backend requested, add to finder for selector
        if backend_arg != "auto":
            finder["backend"] = backend_arg

        executor = _get_unified_executor()
        result = await executor.tap(finder, trace, timeout, device)
        response = {
            "success": result.success,
            "error": result.error,
            "backend": result.backend_used.value if result.backend_used else None,
            "backends_tried": result.backends_tried,
        }
        if result.fallback_occurred:
            response["fallback"] = True
        return response

    elif name == "flutter_double_tap":
        result = await _maestro.double_tap(arguments["finder"], trace, timeout, device)
        return {"success": result.success, "error": result.error_message}

    elif name == "flutter_long_press":
        result = await _maestro.long_press(arguments["finder"], trace, timeout, device)
        return {"success": result.success, "error": result.error_message}

    elif name == "flutter_swipe":
        result = await _maestro.swipe(arguments["direction"], trace, timeout, device)
        return {"success": result.success, "error": result.error_message}

    elif name == "flutter_enter_text":
        result = await _maestro.enter_text(arguments["text"], arguments.get("finder"), trace, timeout, device)
        return {"success": result.success, "error": result.error_message}

    elif name == "flutter_clear_text":
        result = await _maestro.clear_text(trace, timeout, device)
        return {"success": result.success, "error": result.error_message}

    elif name == "flutter_assert_visible":
        backend_arg = arguments.get("backend", "auto")
        finder = arguments["finder"].copy()
        if backend_arg != "auto":
            finder["backend"] = backend_arg

        executor = _get_unified_executor()
        result = await executor.assert_visible(finder, trace, timeout, device)
        response = {
            "success": result.success,
            "error": result.error,
            "backend": result.backend_used.value if result.backend_used else None,
            "backends_tried": result.backends_tried,
        }
        if result.fallback_occurred:
            response["fallback"] = True
        return response

    elif name == "flutter_assert_not_visible":
        result = await _maestro.assert_not_visible(arguments["finder"], trace, timeout, device)
        return {"success": result.success, "error": result.error_message}

    elif name == "flutter_screenshot":
        result = await _maestro.screenshot(trace, timeout, device)
        response = {"success": result.success, "error": result.error_message}
        if result.screenshot_base64:
            response["image"] = result.screenshot_base64
            response["format"] = "png"
            response["encoding"] = "base64"
        return response

    elif name == "flutter_screenshot_adb":
        return await _adb_screenshot(trace, device)

    elif name == "flutter_debug_traces":
        traces = get_recent_traces(arguments.get("count", 5))
        return {"success": True, "traces": traces}

    elif name == "flutter_debug_trace":
        trace_data = get_trace(arguments["trace_id"])
        if trace_data:
            return {"success": True, "trace": trace_data}
        return {"success": False, "error": f"Trace not found: {arguments['trace_id']}"}

    # Phase 2: Flutter Driver tools
    elif name == "flutter_driver_connect":
        uri = arguments.get("uri")
        port = arguments.get("port", OBSERVATORY_PORT_ANDROID)
        host = arguments.get("host", "localhost")
        global _driver_client
        from ..driver import FlutterDriverClient
        _driver_client = FlutterDriverClient(host=host, port=port, uri=uri)
        connected = await _driver_client.connect(trace)
        if connected:
            target = uri if uri else f"{host}:{port}"
            return {"success": True, "message": f"Connected to Observatory at {target}"}
        target = uri if uri else f"{host}:{port}"
        return {"success": False, "error": f"Failed to connect to Observatory at {target}"}

    elif name == "flutter_driver_disconnect":
        if _driver_client:
            await _driver_client.disconnect()
            _driver_client = None
        return {"success": True, "message": "Disconnected"}

    elif name == "flutter_driver_discover":
        device_id = arguments.get("device")
        host_port = arguments.get("host_port", 9223)

        # Discover VM service URI from logcat
        uri = await _discover_vm_service_uri(trace, device_id)
        if not uri:
            return {"success": False, "error": "No VM service URI found. Is a Flutter app with driver extension running?"}

        # Extract port from URI (e.g., http://127.0.0.1:42291/abc=/)
        import re
        port_match = re.search(r":(\d+)/", uri)
        if not port_match:
            return {"success": False, "error": f"Could not parse port from URI: {uri}"}

        device_port = int(port_match.group(1))

        # Set up port forwarding
        if not await _forward_vm_service_port(trace, device_port, host_port, device_id):
            return {"success": False, "error": f"Failed to forward port {device_port} to {host_port}"}

        # Return the forwarded URI (replace device port with host port)
        forwarded_uri = uri.replace(f"127.0.0.1:{device_port}", f"localhost:{host_port}")
        return {
            "success": True,
            "uri": forwarded_uri,
            "device_port": device_port,
            "host_port": host_port,
            "message": f"VM service discovered and forwarded to localhost:{host_port}",
        }

    elif name == "flutter_get_text":
        port = arguments.get("port", OBSERVATORY_PORT_ANDROID)
        if not await _ensure_driver_connected(trace, port):
            return {"success": False, "error": "Not connected to Observatory. Call flutter_driver_connect first or ensure app is running with driver extension."}

        from ..driver.finders import Finder
        finder = Finder.from_dict(arguments["finder"])
        response = await _driver_client.get_text(finder, trace, timeout)
        if response.success and response.response:
            # Flutter Driver returns {"response": "text value", "isError": false}
            text = response.response.get("response") or response.response.get("text")
            return {"success": True, "text": text}
        return {"success": False, "error": response.error or "Failed to get text"}

    elif name == "flutter_widget_tree":
        port = arguments.get("port", OBSERVATORY_PORT_ANDROID)
        if not await _ensure_driver_connected(trace, port):
            return {"success": False, "error": "Not connected to Observatory. Call flutter_driver_connect first or ensure app is running with driver extension."}

        response = await _driver_client.get_render_tree(trace)
        if response.success and response.response:
            # Flutter Driver returns {"response": "tree text", "isError": false}
            tree = response.response.get("response") or response.response.get("tree")
            return {"success": True, "tree": tree}
        return {"success": False, "error": response.error or "Failed to get widget tree"}

    elif name == "flutter_driver_tap":
        port = arguments.get("port", OBSERVATORY_PORT_ANDROID)
        if not await _ensure_driver_connected(trace, port):
            return {"success": False, "error": "Not connected to Observatory. Call flutter_driver_connect first or ensure app is running with driver extension."}

        from ..driver.finders import Finder
        finder = Finder.from_dict(arguments["finder"])
        response = await _driver_client.tap(finder, trace, timeout)
        return {"success": response.success, "error": response.error}

    elif name == "flutter_run":
        project_path = arguments["project_path"]
        port = arguments.get("port", OBSERVATORY_PORT_ANDROID)
        device_arg = arguments.get("device")
        flavor = arguments.get("flavor")

        return await _flutter_run(project_path, port, device_arg, flavor, trace, timeout)

    elif name == "flutter_version":
        # Import version info from server module
        import os
        import platform
        from datetime import datetime
        from pathlib import Path

        start_time = datetime.utcnow()  # Approximate
        port = int(os.environ.get("FLUTTER_CONTROL_PORT", 9225))
        plat = "ios" if port == 9226 else "android"

        # Get deployment time from tools.py mtime
        try:
            tools_file = Path(__file__)
            mtime = tools_file.stat().st_mtime
            deployed_at = datetime.utcfromtimestamp(mtime).isoformat() + "Z"
        except:
            deployed_at = None

        # Get git commit
        git_commit = None
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
                git_commit = result.stdout.strip()
        except:
            pass

        return {
            "success": True,
            "service": "flutter-control",
            "platform": plat,
            "version": "1.0.0",
            "deployed_at": deployed_at,
            "git_commit": git_commit,
            "hostname": platform.node(),
        }

    else:
        return {"success": False, "error": f"Unknown tool: {name}"}
