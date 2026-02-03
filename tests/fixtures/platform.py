"""Platform configuration for integration tests."""

import os
from dataclasses import dataclass
from typing import Optional

# Defaults
DEFAULT_ANDROID_HOST = "phost.local"  # Host Mac from VM via mDNS
DEFAULT_FLUTTER_CONTROL_PORT = 9225   # Flutter Control MCP (UI automation)
DEFAULT_BRIDGE_PORT = 9222            # Android MCP Bridge (emulator lifecycle)
DEFAULT_IOS_HOST = "localhost"        # iOS server runs locally in VM
DEFAULT_IOS_PORT = 9226               # iOS Flutter Control port


@dataclass
class PlatformConfig:
    """Configuration for a test platform (Android or iOS)."""

    name: str  # "android" or "ios"
    mcp_host: str
    mcp_port: int
    bridge_host: Optional[str] = None  # Android MCP Bridge host (same as mcp_host for Android)
    bridge_port: Optional[int] = None  # Android MCP Bridge port
    vm_service_uri: Optional[str] = None  # For driver connection
    device_id: Optional[str] = None

    @property
    def mcp_url(self) -> str:
        """Get the MCP server URL."""
        return f"http://{self.mcp_host}:{self.mcp_port}"

    @property
    def bridge_url(self) -> Optional[str]:
        """Get the Android MCP Bridge URL."""
        if self.bridge_host and self.bridge_port:
            return f"http://{self.bridge_host}:{self.bridge_port}"
        return None

    @property
    def is_android(self) -> bool:
        return self.name == "android"

    @property
    def is_ios(self) -> bool:
        return self.name == "ios"


def get_platform_config() -> PlatformConfig:
    """Get platform configuration from environment variables.

    Environment variables:
        TEST_PLATFORM: "android" or "ios" (default: "android")

        Android (all services on host Mac):
            ANDROID_HOST: Host for all Android services (default: "phost.local")
            FLUTTER_CONTROL_PORT: Flutter Control MCP port (default: 9225)
            BRIDGE_PORT: Android MCP Bridge port (default: 9222)

        iOS (server runs in VM):
            IOS_HOST: Host for iOS MCP server (default: "localhost")
            IOS_PORT: iOS MCP server port (default: 9226)

        Common:
            VM_SERVICE_URI: VM service URI for driver connection
            TEST_DEVICE_ID: Specific device ID to test on

    Note: Android services run on host Mac (phost.local), iOS runs locally in VM.
    """
    platform = os.getenv("TEST_PLATFORM", "android").lower()

    if platform == "android":
        # Single host for all Android services on host Mac
        android_host = os.getenv("ANDROID_HOST", DEFAULT_ANDROID_HOST)
        return PlatformConfig(
            name="android",
            mcp_host=android_host,
            mcp_port=int(os.getenv("FLUTTER_CONTROL_PORT", str(DEFAULT_FLUTTER_CONTROL_PORT))),
            bridge_host=android_host,  # Same host
            bridge_port=int(os.getenv("BRIDGE_PORT", str(DEFAULT_BRIDGE_PORT))),
            vm_service_uri=os.getenv("VM_SERVICE_URI"),
            device_id=os.getenv("TEST_DEVICE_ID"),
        )
    elif platform == "ios":
        return PlatformConfig(
            name="ios",
            mcp_host=os.getenv("IOS_HOST", DEFAULT_IOS_HOST),
            mcp_port=int(os.getenv("IOS_PORT", str(DEFAULT_IOS_PORT))),
            vm_service_uri=os.getenv("VM_SERVICE_URI"),
            device_id=os.getenv("TEST_DEVICE_ID"),
        )
    else:
        raise ValueError(f"Unknown platform: {platform}. Use 'android' or 'ios'.")
