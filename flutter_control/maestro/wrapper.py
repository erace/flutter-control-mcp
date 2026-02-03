"""Wrapper for Maestro CLI execution.

Supports two modes:
1. Fast mode (default): Uses persistent `maestro mcp` process (~250ms/operation)
2. Legacy mode: Spawns `maestro test` for each operation (~14s/operation)

Fast mode is used automatically when available. Falls back to legacy mode
if MCP fails or for operations not supported by MCP.
"""

import asyncio
import base64
import shutil
from typing import Optional, Dict, Any
from pathlib import Path

from .flow_builder import FlowBuilder
from .parser import parse_maestro_output, MaestroResult
from .mcp_client import MaestroMCPClient
from ..logging.trace import TraceContext
from ..config import DEFAULT_TIMEOUT, DEFAULT_APP_ID


class MaestroWrapper:
    """Wraps Maestro CLI for executing UI automation commands."""

    def __init__(self):
        self.maestro_path = self._find_maestro()

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
        """Check if Maestro is installed and available."""
        return self.maestro_path is not None

    async def execute_flow(
        self,
        flow_path: Path,
        trace: TraceContext,
        timeout: int = DEFAULT_TIMEOUT,
        device: Optional[str] = None,
    ) -> MaestroResult:
        """Execute a Maestro flow file."""
        if not self.maestro_path:
            return MaestroResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                error_message="Maestro not installed. Run: curl -Ls 'https://get.maestro.mobile.dev' | bash",
            )

        cmd = [self.maestro_path, "test", str(flow_path)]
        if device:
            cmd.extend(["--device", device])

        trace.log("MAESTRO_CMD", " ".join(cmd))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return MaestroResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    error_message=f"Timeout after {timeout}s",
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            result = parse_maestro_output(process.returncode, stdout_str, stderr_str)

            trace.log("MAESTRO_OUT", f"exit={result.exit_code} {'OK' if result.success else result.error_message}")
            return result

        except Exception as e:
            trace.log("MAESTRO_ERR", str(e))
            return MaestroResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                error_message=str(e),
            )

    async def tap(self, finder: Dict[str, Any], trace: TraceContext, timeout: int = DEFAULT_TIMEOUT, device: Optional[str] = None, app_id: str = DEFAULT_APP_ID) -> MaestroResult:
        """Tap on an element. Uses fast MCP mode when available."""
        # Try fast MCP mode first
        if "text" in finder or "id" in finder:
            try:
                client = await MaestroMCPClient.get_instance()
                result = await client.tap(finder, trace, timeout, device)
                if result.get("success"):
                    return MaestroResult(
                        success=True,
                        exit_code=0,
                        stdout=result.get("content", ""),
                        stderr="",
                        error_message=None
                    )
                # If MCP failed, log and fall through to legacy mode
                trace.log("MCP_FALLBACK", f"MCP tap failed: {result.get('error')}, trying legacy")
            except Exception as e:
                trace.log("MCP_FALLBACK", f"MCP exception: {e}, trying legacy")

        # Legacy mode: spawn maestro test
        builder = FlowBuilder(trace.trace_id, app_id=app_id)
        if "text" in finder:
            builder.tap_text(finder["text"], index=finder.get("index", 0))
        elif "id" in finder:
            builder.tap_id(finder["id"])
        else:
            return MaestroResult(success=False, exit_code=-1, stdout="", stderr="", error_message=f"Unsupported finder: {finder}")
        flow_path = builder.save()
        trace.log("FLOW_SAVED", str(flow_path))
        return await self.execute_flow(flow_path, trace, timeout, device)

    async def double_tap(self, finder: Dict[str, Any], trace: TraceContext, timeout: int = DEFAULT_TIMEOUT, device: Optional[str] = None, app_id: str = DEFAULT_APP_ID) -> MaestroResult:
        """Double tap on an element. Uses fast MCP mode when available."""
        # Try fast MCP mode with run_flow
        if "text" in finder:
            try:
                client = await MaestroMCPClient.get_instance()
                flow_yaml = f"appId: {app_id}\n---\n- doubleTapOn: \"{finder['text']}\""
                result = await client.run_flow(flow_yaml, trace, timeout, device)
                if result.get("success"):
                    return MaestroResult(
                        success=True, exit_code=0,
                        stdout=result.get("content", ""), stderr="", error_message=None
                    )
                trace.log("MCP_FALLBACK", f"MCP double_tap failed: {result.get('error')}, trying legacy")
            except Exception as e:
                trace.log("MCP_FALLBACK", f"MCP exception: {e}, trying legacy")

        # Legacy mode
        builder = FlowBuilder(trace.trace_id, app_id=app_id)
        if "text" in finder:
            builder.double_tap_text(finder["text"])
        else:
            return MaestroResult(success=False, exit_code=-1, stdout="", stderr="", error_message=f"Unsupported finder: {finder}")
        flow_path = builder.save()
        trace.log("FLOW_SAVED", str(flow_path))
        return await self.execute_flow(flow_path, trace, timeout, device)

    async def long_press(self, finder: Dict[str, Any], trace: TraceContext, timeout: int = DEFAULT_TIMEOUT, device: Optional[str] = None, app_id: str = DEFAULT_APP_ID) -> MaestroResult:
        """Long press on an element. Uses fast MCP mode when available."""
        # Try fast MCP mode with run_flow
        if "text" in finder:
            try:
                client = await MaestroMCPClient.get_instance()
                flow_yaml = f"appId: {app_id}\n---\n- longPressOn: \"{finder['text']}\""
                result = await client.run_flow(flow_yaml, trace, timeout, device)
                if result.get("success"):
                    return MaestroResult(
                        success=True, exit_code=0,
                        stdout=result.get("content", ""), stderr="", error_message=None
                    )
                trace.log("MCP_FALLBACK", f"MCP long_press failed: {result.get('error')}, trying legacy")
            except Exception as e:
                trace.log("MCP_FALLBACK", f"MCP exception: {e}, trying legacy")

        # Legacy mode
        builder = FlowBuilder(trace.trace_id, app_id=app_id)
        if "text" in finder:
            builder.long_press_text(finder["text"])
        else:
            return MaestroResult(success=False, exit_code=-1, stdout="", stderr="", error_message=f"Unsupported finder: {finder}")
        flow_path = builder.save()
        trace.log("FLOW_SAVED", str(flow_path))
        return await self.execute_flow(flow_path, trace, timeout, device)

    async def enter_text(self, text: str, finder: Optional[Dict[str, Any]], trace: TraceContext, timeout: int = DEFAULT_TIMEOUT, device: Optional[str] = None, app_id: str = DEFAULT_APP_ID) -> MaestroResult:
        """Enter text, optionally into a specific element. Uses fast MCP mode when available."""
        # Try fast MCP mode
        try:
            client = await MaestroMCPClient.get_instance()
            result = await client.enter_text(text, finder, trace, timeout, device)
            if result.get("success"):
                return MaestroResult(
                    success=True, exit_code=0,
                    stdout=result.get("content", ""), stderr="", error_message=None
                )
            trace.log("MCP_FALLBACK", f"MCP enter_text failed: {result.get('error')}, trying legacy")
        except Exception as e:
            trace.log("MCP_FALLBACK", f"MCP exception: {e}, trying legacy")

        # Legacy mode
        builder = FlowBuilder(trace.trace_id, app_id=app_id)
        element_text = finder.get("text") if finder else None
        element_id = finder.get("id") if finder else None
        builder.enter_text(text, element_text=element_text, element_id=element_id)
        flow_path = builder.save()
        trace.log("FLOW_SAVED", str(flow_path))
        return await self.execute_flow(flow_path, trace, timeout, device)

    async def clear_text(self, trace: TraceContext, timeout: int = DEFAULT_TIMEOUT, device: Optional[str] = None, app_id: str = DEFAULT_APP_ID) -> MaestroResult:
        """Clear the current text field. Uses fast MCP mode when available."""
        # Try fast MCP mode with run_flow
        try:
            client = await MaestroMCPClient.get_instance()
            flow_yaml = f"appId: {app_id}\n---\n- eraseText"
            result = await client.run_flow(flow_yaml, trace, timeout, device)
            if result.get("success"):
                return MaestroResult(
                    success=True, exit_code=0,
                    stdout=result.get("content", ""), stderr="", error_message=None
                )
            trace.log("MCP_FALLBACK", f"MCP clear_text failed: {result.get('error')}, trying legacy")
        except Exception as e:
            trace.log("MCP_FALLBACK", f"MCP exception: {e}, trying legacy")

        # Legacy mode
        builder = FlowBuilder(trace.trace_id, app_id=app_id)
        builder.clear_text()
        flow_path = builder.save()
        trace.log("FLOW_SAVED", str(flow_path))
        return await self.execute_flow(flow_path, trace, timeout, device)

    async def swipe(self, direction: str, trace: TraceContext, timeout: int = DEFAULT_TIMEOUT, device: Optional[str] = None, app_id: str = DEFAULT_APP_ID) -> MaestroResult:
        """Swipe in a direction. Uses fast MCP mode when available."""
        # Map direction to Maestro command
        direction_map = {
            "up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT"
        }
        maestro_dir = direction_map.get(direction.lower(), direction.upper())

        # Try fast MCP mode with run_flow
        try:
            client = await MaestroMCPClient.get_instance()
            flow_yaml = f"appId: {app_id}\n---\n- swipe:\n    direction: {maestro_dir}\n    duration: 400"
            result = await client.run_flow(flow_yaml, trace, timeout, device)
            if result.get("success"):
                return MaestroResult(
                    success=True, exit_code=0,
                    stdout=result.get("content", ""), stderr="", error_message=None
                )
            trace.log("MCP_FALLBACK", f"MCP swipe failed: {result.get('error')}, trying legacy")
        except Exception as e:
            trace.log("MCP_FALLBACK", f"MCP exception: {e}, trying legacy")

        # Legacy mode
        builder = FlowBuilder(trace.trace_id, app_id=app_id)
        builder.swipe(direction)
        flow_path = builder.save()
        trace.log("FLOW_SAVED", str(flow_path))
        return await self.execute_flow(flow_path, trace, timeout, device)

    async def assert_visible(self, finder: Dict[str, Any], trace: TraceContext, timeout: int = DEFAULT_TIMEOUT, device: Optional[str] = None, app_id: str = DEFAULT_APP_ID) -> MaestroResult:
        """Assert an element is visible. Uses fast MCP mode when available."""
        if "text" in finder:
            # Try fast MCP mode with run_flow
            try:
                client = await MaestroMCPClient.get_instance()
                # Use regex for partial matching (same as legacy)
                text = finder["text"]
                flow_yaml = f"appId: {app_id}\n---\n- assertVisible: \".*{text}.*\""
                result = await client.run_flow(flow_yaml, trace, timeout, device)
                if result.get("success"):
                    return MaestroResult(
                        success=True, exit_code=0,
                        stdout=result.get("content", ""), stderr="", error_message=None
                    )
                trace.log("MCP_FALLBACK", f"MCP assert_visible failed: {result.get('error')}, trying legacy")
            except Exception as e:
                trace.log("MCP_FALLBACK", f"MCP exception: {e}, trying legacy")

        # Legacy mode
        builder = FlowBuilder(trace.trace_id, app_id=app_id)
        if "text" in finder:
            builder.assert_visible(finder["text"])
        else:
            return MaestroResult(success=False, exit_code=-1, stdout="", stderr="", error_message=f"Unsupported finder: {finder}")
        flow_path = builder.save()
        trace.log("FLOW_SAVED", str(flow_path))
        return await self.execute_flow(flow_path, trace, timeout, device)

    async def assert_not_visible(self, finder: Dict[str, Any], trace: TraceContext, timeout: int = DEFAULT_TIMEOUT, device: Optional[str] = None, app_id: str = DEFAULT_APP_ID) -> MaestroResult:
        """Assert an element is not visible. Uses fast MCP mode when available."""
        if "text" in finder:
            # Try fast MCP mode with run_flow
            try:
                client = await MaestroMCPClient.get_instance()
                # Use regex for partial matching (same as legacy)
                text = finder["text"]
                flow_yaml = f"appId: {app_id}\n---\n- assertNotVisible: \".*{text}.*\""
                result = await client.run_flow(flow_yaml, trace, timeout, device)
                if result.get("success"):
                    return MaestroResult(
                        success=True, exit_code=0,
                        stdout=result.get("content", ""), stderr="", error_message=None
                    )
                trace.log("MCP_FALLBACK", f"MCP assert_not_visible failed: {result.get('error')}, trying legacy")
            except Exception as e:
                trace.log("MCP_FALLBACK", f"MCP exception: {e}, trying legacy")

        # Legacy mode
        builder = FlowBuilder(trace.trace_id, app_id=app_id)
        if "text" in finder:
            builder.assert_not_visible(finder["text"])
        else:
            return MaestroResult(success=False, exit_code=-1, stdout="", stderr="", error_message=f"Unsupported finder: {finder}")
        flow_path = builder.save()
        trace.log("FLOW_SAVED", str(flow_path))
        return await self.execute_flow(flow_path, trace, timeout, device)

    async def screenshot(self, trace: TraceContext, timeout: int = DEFAULT_TIMEOUT, device: Optional[str] = None, app_id: str = DEFAULT_APP_ID) -> MaestroResult:
        """Take a screenshot and return base64-encoded image. Uses fast MCP mode when available."""
        from ..config import LOG_DIR

        # Try fast MCP mode first
        try:
            client = await MaestroMCPClient.get_instance()
            result = await client.screenshot(trace, timeout, device)
            if result.get("success") and result.get("screenshot_base64"):
                maestro_result = MaestroResult(
                    success=True, exit_code=0,
                    stdout="Screenshot captured via MCP", stderr="", error_message=None
                )
                maestro_result.screenshot_base64 = result["screenshot_base64"]
                trace.log("SCREENSHOT_OK", f"MCP screenshot, {len(result['screenshot_base64'])} chars base64")
                return maestro_result
            trace.log("MCP_FALLBACK", f"MCP screenshot failed: {result.get('error')}, trying legacy")
        except Exception as e:
            trace.log("MCP_FALLBACK", f"MCP exception: {e}, trying legacy")

        # Legacy mode
        screenshot_name = f"screenshot_{trace.trace_id}"
        screenshot_dir = str(LOG_DIR / "screenshots")
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

        builder = FlowBuilder(trace.trace_id, app_id=app_id)
        # Launch app first to ensure it's in foreground
        builder.launch_app()
        # Use absolute path for screenshot
        builder.screenshot(screenshot_name, output_dir=screenshot_dir)
        flow_path = builder.save()
        trace.log("FLOW_SAVED", str(flow_path))

        result = await self.execute_flow(flow_path, trace, timeout, device)

        # Try to read the screenshot file from our known location
        # Maestro adds .png extension automatically
        screenshot_path = Path(screenshot_dir) / f"{screenshot_name}.png"
        trace.log("SCREENSHOT_PATH", str(screenshot_path))
        if screenshot_path.exists():
            try:
                image_data = screenshot_path.read_bytes()
                result.screenshot_base64 = base64.b64encode(image_data).decode("utf-8")
                result.success = True  # Override success if we got the screenshot
                result.error_message = None
                trace.log("SCREENSHOT_OK", f"{len(image_data)} bytes")
            except Exception as e:
                trace.log("SCREENSHOT_ERR", str(e))
        else:
            trace.log("SCREENSHOT_NOT_FOUND", str(screenshot_path))

        return result
