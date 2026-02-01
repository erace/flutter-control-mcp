"""Test environment bootstrap - starts devices and installs apps."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import httpx

# Config
ANDROID_MCP_BRIDGE_HOST = "192.168.64.1"  # Host Mac from VM
ANDROID_MCP_BRIDGE_PORT = 9222
DEFAULT_AVD = "Pixel_7_API_35"
TEST_APP_PACKAGE = "com.example.flutter_control_test_app"
TEST_APP_APK = (
    Path(__file__).parent.parent.parent
    / "test_app/build/app/outputs/flutter-apk/app-debug.apk"
)
IOS_BUNDLE_ID = "com.example.flutterControlTestApp"  # iOS bundle ID format
IOS_APP_PATH = (
    Path(__file__).parent.parent.parent
    / "test_app/build/ios/iphonesimulator/Runner.app"
)
TEST_APP_DIR = Path(__file__).parent.parent.parent / "test_app"


@dataclass
class BootstrapResult:
    """Result of bootstrap operation."""

    platform: str
    device_id: str
    device_started: bool
    app_installed: bool
    app_launched: bool
    driver_connected: bool = False
    driver_uri: str | None = None
    error: str | None = None


class AndroidBootstrap:
    """Bootstrap Android emulator and test app."""

    def __init__(
        self,
        mcp_bridge_host: str,
        mcp_bridge_port: int,
        token: str,
        flutter_control_host: str = "192.168.64.1",
        flutter_control_port: int = 9225,
    ):
        self.bridge_url = f"http://{mcp_bridge_host}:{mcp_bridge_port}"
        self.flutter_url = f"http://{flutter_control_host}:{flutter_control_port}"
        self.token = token

    async def _call_bridge(self, tool: str, args: dict | None = None) -> dict:
        """Call Android MCP Bridge tool (device lifecycle)."""
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.bridge_url}/call",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"name": tool, "arguments": args or {}},
            )
            return resp.json()

    async def _call_flutter(self, tool: str, args: dict | None = None) -> dict:
        """Call Flutter Control MCP tool (driver, tap, etc.)."""
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.flutter_url}/call",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"name": tool, "arguments": args or {}},
            )
            return resp.json()

    async def ensure_emulator_running(self, avd_name: str = DEFAULT_AVD) -> str | None:
        """Start emulator if not running. Returns device_id or None."""
        result = await self._call_bridge("android_list_devices")
        output = result.get("output", "")

        # Parse output for connected devices
        if "emulator-" in output:
            # Already running - extract device ID
            for line in output.split("\n"):
                if "emulator-" in line and "device" in line:
                    return line.split()[0]

        # Start emulator
        start_result = await self._call_bridge(
            "android_start_emulator", {"avd_name": avd_name}
        )
        if start_result.get("success"):
            return start_result.get("device_id", "emulator-5554")
        return None

    async def build_apk(self) -> bool:
        """Build test app APK if it doesn't exist."""
        if TEST_APP_APK.exists():
            return True

        if not TEST_APP_DIR.exists():
            return False

        proc = await asyncio.create_subprocess_exec(
            "flutter",
            "build",
            "apk",
            "--debug",
            cwd=TEST_APP_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0 and TEST_APP_APK.exists()

    async def install_app(self, device_id: str) -> bool:
        """Install test app via ADB. Builds APK if missing."""
        if not await self.build_apk():
            return False

        proc = await asyncio.create_subprocess_exec(
            "adb",
            "-s",
            device_id,
            "install",
            "-r",
            str(TEST_APP_APK),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, _ = await proc.communicate()
        return proc.returncode == 0

    async def launch_app(self, device_id: str) -> bool:
        """Launch test app."""
        proc = await asyncio.create_subprocess_exec(
            "adb",
            "-s",
            device_id,
            "shell",
            "am",
            "start",
            "-n",
            f"{TEST_APP_PACKAGE}/.MainActivity",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def connect_driver(self, device_id: str) -> tuple[bool, str | None]:
        """Discover and connect to Flutter Driver Observatory.

        Returns (success, uri).
        """
        # Discover VM service URI from device logs
        discover_result = await self._call_flutter(
            "flutter_driver_discover", {"device": device_id}
        )
        if not discover_result.get("success"):
            return False, None

        uri = discover_result.get("uri")
        if not uri:
            return False, None

        # Connect to the Observatory
        connect_result = await self._call_flutter(
            "flutter_driver_connect", {"uri": uri}
        )
        if connect_result.get("success"):
            return True, uri
        return False, uri

    async def bootstrap(self, avd_name: str = DEFAULT_AVD) -> BootstrapResult:
        """Full bootstrap: emulator + app install + launch + driver connect."""
        result = BootstrapResult(
            platform="android",
            device_id="",
            device_started=False,
            app_installed=False,
            app_launched=False,
        )
        try:
            device_id = await self.ensure_emulator_running(avd_name)
            if not device_id:
                result.error = "Failed to start emulator"
                return result
            result.device_id = device_id
            result.device_started = True

            # Wait for device to be fully ready
            await asyncio.sleep(2)

            result.app_installed = await self.install_app(device_id)
            if not result.app_installed:
                result.error = "Failed to install app"
                return result

            result.app_launched = await self.launch_app(device_id)
            if not result.app_launched:
                result.error = "Failed to launch app"
                return result

            # Wait for app to start and Observatory to be ready
            await asyncio.sleep(3)

            # Connect to Flutter Driver
            result.driver_connected, result.driver_uri = await self.connect_driver(
                device_id
            )
            if not result.driver_connected:
                # Driver connection is optional - don't fail bootstrap
                # but log the issue
                pass

        except Exception as e:
            result.error = str(e)

        return result


class IOSBootstrap:
    """Bootstrap iOS simulator and test app via MCP server."""

    def __init__(
        self,
        mcp_host: str = "localhost",
        mcp_port: int = 9226,
        token: str = "",
        device_name: str = "iPhone 16e",
    ):
        self.base_url = f"http://{mcp_host}:{mcp_port}"
        self.token = token
        self.device_name = device_name
        self.device_id: str | None = None

    async def _call_mcp(self, tool: str, args: dict | None = None) -> dict:
        """Call iOS MCP server tool."""
        async with httpx.AsyncClient(timeout=120) as client:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            resp = await client.post(
                f"{self.base_url}/call",
                headers=headers,
                json={"name": tool, "arguments": args or {}},
            )
            return resp.json()

    async def ensure_simulator_running(self) -> str | None:
        """Start simulator if not running via MCP. Returns UDID."""
        # Check for booted simulators
        result = await self._call_mcp("ios_list_devices")
        if result.get("success"):
            booted = result.get("booted", [])
            if booted:
                # Already have a booted simulator
                return booted[0]["udid"]

        # Boot simulator by name
        boot_result = await self._call_mcp(
            "ios_boot_simulator", {"device_name": self.device_name}
        )
        if boot_result.get("success"):
            return boot_result.get("device_id")
        return None

    async def build_ios_app(self) -> bool:
        """Build iOS app if not present."""
        if IOS_APP_PATH.exists():
            return True

        if not TEST_APP_DIR.exists():
            return False

        proc = await asyncio.create_subprocess_exec(
            "flutter",
            "build",
            "ios",
            "--simulator",
            "--debug",
            cwd=TEST_APP_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0 and IOS_APP_PATH.exists()

    async def install_app(self, udid: str) -> bool:
        """Install test app to simulator."""
        if not await self.build_ios_app():
            return False

        # Use direct simctl for install (not worth adding MCP tool for this)
        proc = await asyncio.create_subprocess_exec(
            "xcrun",
            "simctl",
            "install",
            udid,
            str(IOS_APP_PATH),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def launch_app(self, udid: str) -> bool:
        """Launch test app on simulator."""
        proc = await asyncio.create_subprocess_exec(
            "xcrun",
            "simctl",
            "launch",
            udid,
            IOS_BUNDLE_ID,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def connect_driver(self, udid: str) -> tuple[bool, str | None]:
        """Discover and connect to Flutter Driver Observatory.

        Returns (success, uri).
        """
        # Discover VM service URI
        discover_result = await self._call_mcp(
            "flutter_driver_discover", {"device": udid}
        )
        if not discover_result.get("success"):
            return False, None

        uri = discover_result.get("uri")
        if not uri:
            return False, None

        # Connect to the Observatory
        connect_result = await self._call_mcp("flutter_driver_connect", {"uri": uri})
        if connect_result.get("success"):
            return True, uri
        return False, uri

    async def bootstrap(self) -> BootstrapResult:
        """Full bootstrap: simulator + app install + launch + driver connect."""
        result = BootstrapResult(
            platform="ios",
            device_id="",
            device_started=False,
            app_installed=False,
            app_launched=False,
        )
        try:
            udid = await self.ensure_simulator_running()
            if not udid:
                result.error = "Failed to boot simulator"
                return result
            result.device_id = udid
            result.device_started = True

            result.app_installed = await self.install_app(udid)
            if not result.app_installed:
                result.error = "Failed to install app"
                return result

            result.app_launched = await self.launch_app(udid)
            if not result.app_launched:
                result.error = "Failed to launch app"
                return result

            # Wait for app to start and Observatory to be ready
            await asyncio.sleep(3)

            # Connect to Flutter Driver
            result.driver_connected, result.driver_uri = await self.connect_driver(
                udid
            )
            if not result.driver_connected:
                # Driver connection is optional - don't fail bootstrap
                pass

        except Exception as e:
            result.error = str(e)

        return result
