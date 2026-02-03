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


async def _rediscover_driver(trace) -> "FlutterDriverClient":
    """Rediscover and reconnect to Flutter Driver. Returns new client or None."""
    global _driver_client
    from ..driver import FlutterDriverClient

    trace.log("REDISCOVER_START", "Discovering fresh VM service URI")
    uri = await _discover_vm_service_uri(trace)
    if not uri:
        trace.log("REDISCOVER_FAIL", "No VM service URI found")
        return None

    # Extract port and set up forwarding
    import re
    port_match = re.search(r":(\d+)/", uri)
    if not port_match:
        return None

    device_port = int(port_match.group(1))
    host_port = OBSERVATORY_PORT_ANDROID
    if not await _forward_vm_service_port(trace, device_port, host_port):
        return None

    # Create new client with fresh URI
    forwarded_uri = uri.replace(f"127.0.0.1:{device_port}", f"localhost:{host_port}")
    _driver_client = FlutterDriverClient(port=host_port, uri=forwarded_uri)

    if await _driver_client.connect(trace):
        trace.log("REDISCOVER_OK", f"Connected: {forwarded_uri}")
        return _driver_client

    return None


def _get_unified_executor():
    """Get or create unified executor."""
    global _unified_executor
    if _unified_executor is None:
        from ..unified import UnifiedExecutor
        _unified_executor = UnifiedExecutor(_maestro, _get_driver_client(), rediscover_callback=_rediscover_driver)
    return _unified_executor


async def _ensure_driver_connected(trace: TraceContext, port: int = OBSERVATORY_PORT_ANDROID) -> bool:
    """Ensure driver is connected, with auto-rediscovery if needed."""
    global _driver_client, _unified_executor
    client = _get_driver_client(port)

    # If already connected, we're good
    if client.is_connected:
        return True

    # Try to reconnect with existing URI
    if client._uri:
        trace.log("DRIVER_RECONNECT", "Attempting reconnect with existing URI")
        if await client.connect(trace):
            return True
        trace.log("DRIVER_RECONNECT_FAIL", "Reconnect failed, will rediscover")

    # Rediscover VM service URI
    trace.log("DRIVER_REDISCOVER", "Discovering fresh VM service URI")
    uri = await _discover_vm_service_uri(trace)
    if not uri:
        trace.log("DRIVER_ERR", "No VM service URI found during rediscovery")
        return False

    # Extract port and set up forwarding
    import re
    port_match = re.search(r":(\d+)/", uri)
    if not port_match:
        trace.log("DRIVER_ERR", f"Could not parse port from URI: {uri}")
        return False

    device_port = int(port_match.group(1))
    if not await _forward_vm_service_port(trace, device_port, port):
        trace.log("DRIVER_ERR", f"Failed to forward port {device_port}")
        return False

    # Create new client with fresh URI
    forwarded_uri = uri.replace(f"127.0.0.1:{device_port}", f"localhost:{port}")
    from ..driver import FlutterDriverClient
    _driver_client = FlutterDriverClient(port=port, uri=forwarded_uri)
    _unified_executor = None  # Reset executor to pick up new client

    if await _driver_client.connect(trace):
        trace.log("DRIVER_RECONNECTED", f"Connected with fresh URI: {forwarded_uri}")
        return True

    trace.log("DRIVER_ERR", "Failed to connect with fresh URI")
    return False

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
    """Discover VM service URI using mDNS (preferred), with logcat fallback for Android."""
    import os
    import re

    def _extract_uri(output: str) -> Optional[str]:
        """Extract VM service URI from log output."""
        for line in reversed(output.split("\n")):
            if "Dart VM service is listening on" in line or "Observatory listening on" in line:
                match = re.search(r"http://[^\s]+", line)
                if match:
                    return match.group(0)
        return None

    # Detect platform from server port (9226=iOS, 9225=Android) or device UDID
    server_port = int(os.getenv("FLUTTER_CONTROL_PORT", "9225"))
    is_ios_server = server_port == 9226
    is_ios_udid = device and len(device) == 36 and device.count("-") == 4
    is_ios = is_ios_server or is_ios_udid

    # Try mDNS first (works on both iOS and Android, this is how Flutter does it)
    # The VM service advertises via Bonjour with the auth code in TXT record
    try:
        # Step 1: Browse for _dartVmService._tcp services
        # dns-sd runs continuously, so we read lines until we find what we need
        process = await asyncio.create_subprocess_exec(
            "dns-sd", "-B", "_dartVmService._tcp", "local.",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        service_name = None
        try:
            # Read lines until we find a service or timeout
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 2:
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=0.5)
                    if line:
                        decoded = line.decode()
                        if "_dartVmService._tcp." in decoded and "Add" in decoded:
                            parts = decoded.split()
                            if len(parts) >= 7:
                                service_name = parts[-1]
                                break
                except asyncio.TimeoutError:
                    continue
        finally:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=1)
            except asyncio.TimeoutError:
                process.kill()

        if service_name:
            trace.log("MDNS_FOUND", f"Service: {service_name}")

            # Step 2: Lookup service details to get port and auth code
            process = await asyncio.create_subprocess_exec(
                "dns-sd", "-L", service_name, "_dartVmService._tcp", "local.",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            port = None
            auth_code = None
            try:
                start_time = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start_time < 2:
                    try:
                        line = await asyncio.wait_for(process.stdout.readline(), timeout=0.5)
                        if line:
                            decoded = line.decode()
                            # Port: "can be reached at hostname:PORT"
                            port_match = re.search(r":(\d+)\s", decoded)
                            if port_match:
                                port = port_match.group(1)
                            # Auth code: "authCode=XXXXX"
                            auth_match = re.search(r"authCode=(\S+)", decoded)
                            if auth_match:
                                auth_code = auth_match.group(1)
                            # Once we have both, we're done
                            if port and auth_code:
                                break
                    except asyncio.TimeoutError:
                        continue
            finally:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=1)
                except asyncio.TimeoutError:
                    process.kill()

            if port and auth_code:
                uri = f"http://127.0.0.1:{port}/{auth_code}/"
                trace.log("DISCOVER_URI", f"mDNS: {uri}")
                return uri
            elif port:
                uri = f"http://127.0.0.1:{port}/"
                trace.log("DISCOVER_URI", f"mDNS (no auth): {uri}")
                return uri

        trace.log("MDNS_NOT_FOUND", "No Dart VM service advertised via mDNS")
    except Exception as e:
        trace.log("MDNS_ERR", str(e))

    # Fallback for Android: try logcat
    if not is_ios and _adb_path:
        trace.log("DISCOVER_FALLBACK", "Trying Android logcat")
        try:
            cmd = [_adb_path]
            if device:
                cmd.extend(["-s", device])
            cmd.extend(["logcat", "-d", "-t", "100", "*:I"])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)
            output = stdout.decode("utf-8", errors="replace")

            uri = _extract_uri(output)
            if uri:
                trace.log("DISCOVER_URI", f"logcat: {uri}")
                return uri
            trace.log("DISCOVER_LOGCAT_EMPTY", "No VM service URI in logcat")
        except Exception as e:
            trace.log("DISCOVER_LOGCAT_ERR", str(e))

    # Last resort for iOS: port scan (finds port but not auth code)
    if is_ios:
        trace.log("DISCOVER_FALLBACK", "Trying iOS port scan")
        try:
            process = await asyncio.create_subprocess_shell(
                "/usr/sbin/lsof -i -P -n | grep -E '^Runner.*LISTEN'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
            output = stdout.decode()

            for line in output.split("\n"):
                if "127.0.0.1:" in line:
                    match = re.search(r"127\.0\.0\.1:(\d+)", line)
                    if match:
                        port = match.group(1)
                        uri = f"http://127.0.0.1:{port}/"
                        trace.log("DISCOVER_URI", f"port scan (no auth): {uri}")
                        return uri
        except Exception as e:
            trace.log("DISCOVER_PORTSCAN_ERR", str(e))

    return None


async def _forward_vm_service_port(trace: TraceContext, device_port: int, host_port: int = 9223, device: Optional[str] = None, is_ios: bool = False) -> bool:
    """Forward VM service port from device to host.

    For iOS simulator, no forwarding is needed (returns True immediately).
    For Android, uses adb forward.
    """
    # iOS simulator runs on same machine - no port forwarding needed
    if is_ios:
        trace.log("FORWARD_SKIP", "iOS simulator - no forwarding needed")
        return True

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


async def _simctl_screenshot(trace: TraceContext, device: Optional[str] = None) -> Dict[str, Any]:
    """Take screenshot using xcrun simctl (iOS simulator)."""
    import tempfile
    import os

    # Use booted device if not specified
    device_arg = device or "booted"

    # Create temp file for screenshot
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        temp_path = f.name

    try:
        cmd = ["xcrun", "simctl", "io", device_arg, "screenshot", temp_path]
        trace.log("SIMCTL_CMD", " ".join(cmd))

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=10)

        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace")
            trace.log("SIMCTL_ERR", error)
            return {"success": False, "error": f"simctl failed: {error}"}

        # Read the screenshot file
        with open(temp_path, "rb") as f:
            image_data = f.read()

        if len(image_data) < 100:
            trace.log("SIMCTL_ERR", "Empty or invalid screenshot")
            return {"success": False, "error": "Empty screenshot"}

        image_b64 = base64.b64encode(image_data).decode("utf-8")
        trace.log("SIMCTL_OK", f"{len(image_data)} bytes")

        return {
            "success": True,
            "error": None,
            "image": image_b64,
            "format": "png",
            "encoding": "base64",
        }
    except asyncio.TimeoutError:
        trace.log("SIMCTL_ERR", "Timeout")
        return {"success": False, "error": "simctl timeout"}
    except Exception as e:
        trace.log("SIMCTL_ERR", str(e))
        return {"success": False, "error": str(e)}
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass


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

    # Build command (use new vm service port flags, not deprecated --observatory-port)
    cmd = [
        flutter_path,
        "run",
        "--device-vmservice-port", str(port),
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
        import re as re_module
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

                    # Check for Observatory URL (extract full URI with auth token)
                    if "vm service" in decoded.lower() or "observatory" in decoded.lower():
                        # Extract full URI: http://127.0.0.1:PORT/AUTH_TOKEN=/
                        uri_match = re_module.search(r"http://[^\s]+", decoded)
                        if uri_match:
                            observatory_uri = uri_match.group(0)
                            trace.log("FLUTTER_READY", f"Observatory at {observatory_uri}")
                            return {
                                "success": True,
                                "message": f"App running with Observatory",
                                "uri": observatory_uri,
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


async def _ios_list_devices(trace: TraceContext) -> Dict[str, Any]:
    """List iOS simulators using xcrun simctl."""
    import json as json_module

    try:
        process = await asyncio.create_subprocess_exec(
            "xcrun", "simctl", "list", "devices", "-j",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace")
            trace.log("SIMCTL_ERR", error)
            return {"success": False, "error": f"simctl failed: {error}"}

        data = json_module.loads(stdout.decode("utf-8"))
        devices = data.get("devices", {})

        # Find booted devices
        booted = []
        available = []
        for runtime, device_list in devices.items():
            for device in device_list:
                if device.get("isAvailable", False):
                    device_info = {
                        "name": device["name"],
                        "udid": device["udid"],
                        "state": device["state"],
                        "runtime": runtime.split(".")[-1] if "." in runtime else runtime,
                    }
                    if device["state"] == "Booted":
                        booted.append(device_info)
                    available.append(device_info)

        trace.log("SIMCTL_OK", f"{len(booted)} booted, {len(available)} available")
        return {
            "success": True,
            "booted": booted,
            "available": available,
            "output": f"{len(booted)} booted, {len(available)} available simulators",
        }
    except asyncio.TimeoutError:
        trace.log("SIMCTL_ERR", "Timeout")
        return {"success": False, "error": "simctl timeout"}
    except Exception as e:
        trace.log("SIMCTL_ERR", str(e))
        return {"success": False, "error": str(e)}


async def _ios_boot_simulator(
    trace: TraceContext, device_name: Optional[str] = None, udid: Optional[str] = None
) -> Dict[str, Any]:
    """Boot an iOS simulator by name or UDID."""
    import json as json_module

    # If no UDID provided, find it by name
    if not udid and device_name:
        try:
            process = await asyncio.create_subprocess_exec(
                "xcrun", "simctl", "list", "devices", "-j",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30)
            data = json_module.loads(stdout.decode("utf-8"))

            for _runtime, device_list in data.get("devices", {}).items():
                for device in device_list:
                    if device["name"] == device_name and device.get("isAvailable", False):
                        udid = device["udid"]
                        break
                if udid:
                    break

            if not udid:
                return {"success": False, "error": f"Simulator not found: {device_name}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to find simulator: {e}"}

    if not udid:
        return {"success": False, "error": "No device_name or udid provided"}

    # Check if already booted
    try:
        process = await asyncio.create_subprocess_exec(
            "xcrun", "simctl", "list", "devices", "-j",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30)
        data = json_module.loads(stdout.decode("utf-8"))

        for _runtime, device_list in data.get("devices", {}).items():
            for device in device_list:
                if device["udid"] == udid and device["state"] == "Booted":
                    trace.log("SIMCTL_BOOT", f"Already booted: {udid}")
                    return {
                        "success": True,
                        "device_id": udid,
                        "message": "Simulator already booted",
                    }
    except Exception:
        pass

    # Boot the simulator
    trace.log("SIMCTL_BOOT", f"Booting {udid}")
    try:
        process = await asyncio.create_subprocess_exec(
            "xcrun", "simctl", "boot", udid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=120)

        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace")
            # "Unable to boot device in current state: Booted" is not an error
            if "Booted" in error:
                return {"success": True, "device_id": udid, "message": "Simulator already booted"}
            trace.log("SIMCTL_ERR", error)
            return {"success": False, "error": f"Failed to boot: {error}"}

        # Wait for simulator to be ready
        await asyncio.sleep(5)

        trace.log("SIMCTL_OK", f"Booted {udid}")
        return {
            "success": True,
            "device_id": udid,
            "message": "Simulator booted successfully",
        }
    except asyncio.TimeoutError:
        trace.log("SIMCTL_ERR", "Boot timeout")
        return {"success": False, "error": "Simulator boot timeout"}
    except Exception as e:
        trace.log("SIMCTL_ERR", str(e))
        return {"success": False, "error": str(e)}


async def _ios_shutdown_simulator(trace: TraceContext, udid: Optional[str] = None) -> Dict[str, Any]:
    """Shutdown an iOS simulator."""
    import json as json_module

    # If no UDID, find the first booted simulator
    if not udid:
        try:
            process = await asyncio.create_subprocess_exec(
                "xcrun", "simctl", "list", "devices", "-j",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30)
            data = json_module.loads(stdout.decode("utf-8"))

            for _runtime, device_list in data.get("devices", {}).items():
                for device in device_list:
                    if device["state"] == "Booted":
                        udid = device["udid"]
                        break
                if udid:
                    break

            if not udid:
                return {"success": True, "message": "No booted simulators to shutdown"}
        except Exception as e:
            return {"success": False, "error": f"Failed to find simulator: {e}"}

    trace.log("SIMCTL_SHUTDOWN", udid)
    try:
        process = await asyncio.create_subprocess_exec(
            "xcrun", "simctl", "shutdown", udid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=60)

        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace")
            trace.log("SIMCTL_ERR", error)
            return {"success": False, "error": f"Failed to shutdown: {error}"}

        trace.log("SIMCTL_OK", f"Shutdown {udid}")
        return {"success": True, "device_id": udid, "message": "Simulator shutdown"}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Shutdown timeout"}
    except Exception as e:
        trace.log("SIMCTL_ERR", str(e))
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
        "description": "Assert that an element is NOT visible on screen. Auto-selects backend with fallback.",
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
        "name": "flutter_screenshot",
        "description": "Take a screenshot. Auto-selects fastest method: ADB (Android) or simctl (iOS). Falls back to Maestro on error.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device ID (default: first device)"},
            },
        },
    },
    {
        "name": "flutter_screenshot_maestro",
        "description": "Take a screenshot using Maestro (slower but works when native methods fail).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "timeout": {"type": "integer"},
                "device": {"type": "string"},
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
    # iOS Simulator lifecycle tools
    {
        "name": "ios_list_devices",
        "description": "List iOS simulators and their status. Returns available simulators grouped by runtime.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "ios_boot_simulator",
        "description": "Boot an iOS simulator by name or UDID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_name": {"type": "string", "description": "Simulator name (e.g., 'iPhone 16e')"},
                "udid": {"type": "string", "description": "Simulator UDID (takes precedence over device_name)"},
            },
        },
    },
    {
        "name": "ios_shutdown_simulator",
        "description": "Shutdown an iOS simulator.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "udid": {"type": "string", "description": "Simulator UDID (default: first booted simulator)"},
            },
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
        backend_arg = arguments.get("backend", "auto")
        finder = arguments["finder"].copy()
        if backend_arg != "auto":
            finder["backend"] = backend_arg

        executor = _get_unified_executor()
        result = await executor.assert_not_visible(finder, trace, timeout, device)
        response = {
            "success": result.success,
            "error": result.error,
            "backend": result.backend_used.value if result.backend_used else None,
        }
        if result.fallback_occurred:
            response["fallback"] = True
        return response

    elif name == "flutter_screenshot":
        # Smart screenshot: detect platform, use native method, fallback to Maestro
        import os as os_mod
        server_port = int(os_mod.environ.get("FLUTTER_CONTROL_PORT", "9225"))
        is_ios = server_port == 9226

        if is_ios:
            # Try simctl first
            result = await _simctl_screenshot(trace, device)
            if result.get("success"):
                result["method"] = "simctl"
                return result
            trace.log("SCREENSHOT_FALLBACK", f"simctl failed: {result.get('error')}, trying Maestro")
        else:
            # Try ADB first
            result = await _adb_screenshot(trace, device)
            if result.get("success"):
                result["method"] = "adb"
                return result
            trace.log("SCREENSHOT_FALLBACK", f"ADB failed: {result.get('error')}, trying Maestro")

        # Fallback to Maestro
        maestro_result = await _maestro.screenshot(trace, timeout, device)
        response = {"success": maestro_result.success, "error": maestro_result.error_message, "method": "maestro"}
        if maestro_result.screenshot_base64:
            response["image"] = maestro_result.screenshot_base64
            response["format"] = "png"
            response["encoding"] = "base64"
        return response

    elif name == "flutter_screenshot_maestro":
        # Explicit Maestro screenshot
        result = await _maestro.screenshot(trace, timeout, device)
        response = {"success": result.success, "error": result.error_message, "method": "maestro"}
        if result.screenshot_base64:
            response["image"] = result.screenshot_base64
            response["format"] = "png"
            response["encoding"] = "base64"
        return response

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
        global _driver_client, _unified_executor
        from ..driver import FlutterDriverClient
        _driver_client = FlutterDriverClient(host=host, port=port, uri=uri)
        # Reset unified executor so it picks up the new driver client
        _unified_executor = None
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
        import os as os_module
        device_id = arguments.get("device")
        host_port = arguments.get("host_port", 9223)

        # Detect iOS: server port 9226 or device ID is a UDID
        server_port = int(os_module.environ.get("FLUTTER_CONTROL_PORT", "9225"))
        is_ios_server = server_port == 9226
        is_ios_udid = device_id and len(device_id) == 36 and device_id.count("-") == 4
        is_ios = is_ios_server or is_ios_udid

        # Discover VM service URI from device logs
        uri = await _discover_vm_service_uri(trace, device_id)
        if not uri:
            return {"success": False, "error": "No VM service URI found. Is a Flutter app with driver extension running?"}

        # Extract port from URI (e.g., http://127.0.0.1:42291/abc=/)
        import re
        port_match = re.search(r":(\d+)/", uri)
        if not port_match:
            return {"success": False, "error": f"Could not parse port from URI: {uri}"}

        device_port = int(port_match.group(1))

        # Set up port forwarding (not needed for iOS simulator)
        if not await _forward_vm_service_port(trace, device_port, host_port, device_id, is_ios=is_ios):
            return {"success": False, "error": f"Failed to forward port {device_port} to {host_port}"}

        # For iOS, use URI as-is; for Android, use forwarded URI
        if is_ios:
            result_uri = uri
            message = f"VM service discovered at {uri}"
        else:
            result_uri = uri.replace(f"127.0.0.1:{device_port}", f"localhost:{host_port}")
            message = f"VM service discovered and forwarded to localhost:{host_port}"

        return {
            "success": True,
            "uri": result_uri,
            "device_port": device_port,
            "host_port": host_port if not is_ios else device_port,
            "message": message,
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
        # Import version info from package
        import os
        import platform
        from datetime import datetime
        from pathlib import Path
        from .. import __version__

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
            "version": __version__,
            "deployed_at": deployed_at,
            "git_commit": git_commit,
            "hostname": platform.node(),
        }

    # iOS Simulator lifecycle tools
    elif name == "ios_list_devices":
        return await _ios_list_devices(trace)

    elif name == "ios_boot_simulator":
        device_name = arguments.get("device_name")
        udid = arguments.get("udid")
        return await _ios_boot_simulator(trace, device_name, udid)

    elif name == "ios_shutdown_simulator":
        udid = arguments.get("udid")
        return await _ios_shutdown_simulator(trace, udid)

    else:
        return {"success": False, "error": f"Unknown tool: {name}"}
