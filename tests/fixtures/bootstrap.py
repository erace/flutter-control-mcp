"""Test environment bootstrap - uses MCP tools to start devices and apps."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx

# Config
TEST_APP_DIR = Path(__file__).parent.parent.parent / "test_app"

# Common Android SDK locations
ANDROID_SDK_PATHS = [
    Path.home() / "Library" / "Android" / "sdk" / "platform-tools" / "adb",
    Path("/usr/local/android-sdk/platform-tools/adb"),
    Path("/opt/android-sdk/platform-tools/adb"),
]


def find_adb() -> str:
    """Find adb binary - checks PATH first, then common locations."""
    # First check PATH
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path

    # Check common SDK locations
    for path in ANDROID_SDK_PATHS:
        if path.exists():
            return str(path)

    # Last resort: assume it's in PATH and let subprocess fail with clear error
    return "adb"


def get_adb_env() -> dict:
    """Get environment for ADB subprocess with ADB_SERVER_SOCKET set."""
    env = os.environ.copy()
    # Ensure ADB_SERVER_SOCKET is set for remote ADB access
    if "ADB_SERVER_SOCKET" not in env:
        android_host = os.getenv("ANDROID_HOST", "phost.local")
        env["ADB_SERVER_SOCKET"] = f"tcp:{android_host}:15037"
    return env
TEST_APP_PACKAGE = "com.example.flutter_control_test_app"
TEST_APP_BUNDLE_ID = "com.example.flutterControlTestApp"
TEST_APP_APK = TEST_APP_DIR / "build" / "app" / "outputs" / "flutter-apk" / "app-debug.apk"
TEST_APP_IOS = TEST_APP_DIR / "build" / "ios" / "iphonesimulator" / "Runner.app"


@dataclass
class BootstrapResult:
    """Result of bootstrap operation."""

    platform: str
    device_id: str
    device_started: bool
    app_launched: bool
    driver_connected: bool = False
    driver_uri: str | None = None
    error: str | None = None


class MCPBootstrap:
    """Bootstrap using MCP tools - works for both Android and iOS."""

    def __init__(
        self,
        mcp_host: str,
        mcp_port: int,
        token: str,
        platform: str,
        bridge_host: str | None = None,
        bridge_port: int | None = None,
    ):
        self.mcp_url = f"http://{mcp_host}:{mcp_port}"
        self.bridge_url = f"http://{bridge_host}:{bridge_port}" if bridge_host else None
        self.token = token
        self.platform = platform

    async def _call_mcp(self, tool: str, args: dict | None = None, timeout: int = 120) -> dict:
        """Call MCP tool."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            resp = await client.post(
                f"{self.mcp_url}/call",
                headers=headers,
                json={"name": tool, "arguments": args or {}},
            )
            return resp.json()

    async def _call_bridge(self, tool: str, args: dict | None = None, timeout: int = 120) -> dict:
        """Call Android MCP Bridge tool."""
        if not self.bridge_url:
            return {"success": False, "error": "No bridge configured"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            resp = await client.post(
                f"{self.bridge_url}/call",
                headers=headers,
                json={"name": tool, "arguments": args or {}},
            )
            return resp.json()

    async def ensure_device_running(self) -> str | None:
        """Ensure device/emulator is running. Returns device ID."""
        if self.platform == "android":
            # Check if emulator already running via flutter-control
            result = await self._call_mcp("android_list_devices")
            running = result.get("running", [])
            if running:
                return running[0].get("id", "emulator-5554")

            # Start emulator
            avd_name = os.getenv("ANDROID_AVD_NAME", "Pixel_7_API_35")
            start_result = await self._call_mcp(
                "android_start_emulator",
                {"avd_name": avd_name},
                timeout=180
            )
            if start_result.get("success"):
                await asyncio.sleep(5)  # Wait for emulator to be fully ready
                return start_result.get("device_id", "emulator-5554")
            return None
        else:
            # iOS - check for booted simulators via MCP
            result = await self._call_mcp("ios_list_devices")
            if result.get("success"):
                booted = result.get("booted", [])
                if booted:
                    return booted[0]["udid"]

            # Start simulator (renamed from boot)
            device_name = os.getenv("IOS_SIMULATOR_NAME", "iPhone 16e")
            start_result = await self._call_mcp(
                "ios_start_simulator",
                {"device_name": device_name},
                timeout=60
            )
            if start_result.get("success"):
                await asyncio.sleep(3)
                return start_result.get("device_id")
            return None

    async def install_app(self, device_id: str) -> bool:
        """Install pre-built app to device."""
        if self.platform == "android":
            if not TEST_APP_APK.exists():
                print(f"  ⚠ APK not found at {TEST_APP_APK}")
                print(f"  Build it with: cd test_app && flutter build apk --debug")
                return False
            # Use adb install with proper env for remote ADB access
            adb = find_adb()
            env = get_adb_env()
            proc = await asyncio.create_subprocess_exec(
                adb, "-s", device_id, "install", "-r", str(TEST_APP_APK),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                print(f"  ⚠ Install failed: {stderr.decode()}")
                return False
            return True
        else:
            # iOS: Install via simctl
            if not TEST_APP_IOS.exists():
                print(f"  ⚠ iOS app not found at {TEST_APP_IOS}")
                print(f"  Build it with: cd test_app && flutter build ios --simulator --debug")
                return False
            proc = subprocess.run(
                ["xcrun", "simctl", "install", device_id, str(TEST_APP_IOS)],
                capture_output=True, text=True
            )
            if proc.returncode != 0:
                print(f"  ⚠ Install failed: {proc.stderr}")
                return False
            return True

    async def launch_app(self, device_id: str) -> bool:
        """Launch the app on device."""
        if self.platform == "android":
            adb = find_adb()
            env = get_adb_env()
            proc = await asyncio.create_subprocess_exec(
                adb, "-s", device_id, "shell", "am", "start",
                "-n", f"{TEST_APP_PACKAGE}/.MainActivity",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            await proc.communicate()
            return proc.returncode == 0
        else:
            # iOS: Launch via simctl
            proc = subprocess.run(
                ["xcrun", "simctl", "launch", device_id, TEST_APP_BUNDLE_ID],
                capture_output=True, text=True
            )
            return proc.returncode == 0

    async def discover_and_connect_driver(self, device_id: str) -> tuple[bool, str | None]:
        """Discover Observatory URI via mDNS and connect to Flutter Driver.

        Returns (success, uri).
        """
        # Wait for app to start and advertise via mDNS
        await asyncio.sleep(2)

        # Discover URI (uses mDNS on iOS, logcat on Android)
        result = await self._call_mcp(
            "flutter_driver_discover",
            {"device": device_id},
            timeout=30
        )

        if not result.get("success"):
            print(f"  ℹ Driver discovery: {result.get('error', 'not found')}")
            return False, None

        uri = result.get("uri")
        if not uri:
            return False, None

        # Connect to driver
        connect_result = await self._call_mcp(
            "flutter_driver_connect",
            {"uri": uri}
        )

        return connect_result.get("success", False), uri

    async def bootstrap(self) -> BootstrapResult:
        """Full bootstrap using MCP tools.

        Flow for both platforms:
        1. Start emulator/simulator if needed (MCP tools)
        2. Install pre-built app (adb/simctl)
        3. Launch app (adb/simctl)
        4. Discover Observatory URL (mDNS for iOS, logcat for Android)
        5. Connect driver
        """
        result = BootstrapResult(
            platform=self.platform,
            device_id="",
            device_started=False,
            app_launched=False,
        )

        try:
            # 1. Ensure device is running
            device_id = await self.ensure_device_running()
            if not device_id:
                result.error = "Failed to start device/emulator"
                return result
            result.device_id = device_id
            result.device_started = True

            # 2. Install pre-built app
            installed = await self.install_app(device_id)
            if not installed:
                result.error = "Failed to install app (is it built?)"
                return result

            # 3. Launch app
            launched = await self.launch_app(device_id)
            if not launched:
                result.error = "Failed to launch app"
                return result
            result.app_launched = True

            # 4 & 5. Discover Observatory and connect driver
            result.driver_connected, result.driver_uri = await self.discover_and_connect_driver(device_id)

        except Exception as e:
            result.error = str(e)

        return result


# Convenience aliases for backwards compatibility
class AndroidBootstrap(MCPBootstrap):
    """Bootstrap for Android."""

    def __init__(
        self,
        token: str,
        flutter_control_host: str = "phost.local",
        flutter_control_port: int = 9225,
        # Legacy params (ignored - bridge merged into flutter-control)
        mcp_bridge_host: str = None,
        mcp_bridge_port: int = None,
    ):
        super().__init__(
            mcp_host=flutter_control_host,
            mcp_port=flutter_control_port,
            token=token,
            platform="android",
        )


class IOSBootstrap(MCPBootstrap):
    """Bootstrap for iOS."""

    def __init__(
        self,
        mcp_host: str = "localhost",
        mcp_port: int = 9226,
        token: str = "",
        device_name: str = "iPhone 16e",
    ):
        super().__init__(
            mcp_host=mcp_host,
            mcp_port=mcp_port,
            token=token,
            platform="ios",
        )
        # Store device_name for ensure_device_running
        os.environ.setdefault("IOS_SIMULATOR_NAME", device_name)
