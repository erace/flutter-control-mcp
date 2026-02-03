"""Platform configuration for integration tests."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PlatformConfig:
    """Configuration for a test platform (Android or iOS)."""

    name: str  # "android" or "ios"
    mcp_host: str
    mcp_port: int
    vm_service_uri: Optional[str] = None  # For driver connection
    device_id: Optional[str] = None

    @property
    def mcp_url(self) -> str:
        """Get the MCP server URL."""
        return f"http://{self.mcp_host}:{self.mcp_port}"

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
        ANDROID_MCP_HOST: Host for Android MCP server (default: "phost.local" - host Mac from VM)
        ANDROID_MCP_PORT: Port for Android MCP server (default: 9225)
        IOS_MCP_HOST: Host for iOS MCP server (default: "localhost")
        IOS_MCP_PORT: Port for iOS MCP server (default: 9226)
        IOS_VM_SERVICE_URI: VM service URI for iOS driver connection
        ANDROID_VM_SERVICE_URI: VM service URI for Android driver connection
        TEST_DEVICE_ID: Specific device ID to test on

    Note: Android MCP server runs on host Mac (phost.local), iOS MCP server runs on VM (localhost).
    """
    platform = os.getenv("TEST_PLATFORM", "android").lower()

    if platform == "android":
        # Android MCP server runs on host Mac - use host IP from VM
        return PlatformConfig(
            name="android",
            mcp_host=os.getenv("ANDROID_MCP_HOST", "phost.local"),
            mcp_port=int(os.getenv("ANDROID_MCP_PORT", "9225")),
            vm_service_uri=os.getenv("ANDROID_VM_SERVICE_URI"),
            device_id=os.getenv("TEST_DEVICE_ID"),
        )
    elif platform == "ios":
        return PlatformConfig(
            name="ios",
            mcp_host=os.getenv("IOS_MCP_HOST", "localhost"),
            mcp_port=int(os.getenv("IOS_MCP_PORT", "9226")),
            vm_service_uri=os.getenv("IOS_VM_SERVICE_URI"),
            device_id=os.getenv("TEST_DEVICE_ID"),
        )
    else:
        raise ValueError(f"Unknown platform: {platform}. Use 'android' or 'ios'.")
