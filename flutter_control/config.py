"""Configuration for Flutter Control."""

import os
from pathlib import Path

# Server
MCP_HOST = os.getenv("FLUTTER_CONTROL_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("FLUTTER_CONTROL_PORT", "9225"))

# Auth - shared with android-mcp-bridge
TOKEN_FILE = Path.home() / ".android-mcp-token"
TOKEN = os.getenv("FLUTTER_CONTROL_TOKEN") or (
    TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else None
)

# Timeouts
DEFAULT_TIMEOUT = int(os.getenv("FLUTTER_CONTROL_TIMEOUT", "30"))

# Observatory ports (Flutter VM Service)
OBSERVATORY_PORT_ANDROID = int(os.getenv("FLUTTER_CONTROL_OBSERVATORY_ANDROID", "9223"))
OBSERVATORY_PORT_IOS = int(os.getenv("FLUTTER_CONTROL_OBSERVATORY_IOS", "9224"))

# Default app ID for Maestro (can be overridden per-call)
DEFAULT_APP_ID = os.getenv("FLUTTER_CONTROL_APP_ID", "com.example.flutter_control_test_app")

# Logging
LOG_DIR = Path.home() / "Library" / "Logs" / "flutter-control"
MAESTRO_FLOW_DIR = LOG_DIR / "maestro"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
MAESTRO_FLOW_DIR.mkdir(parents=True, exist_ok=True)
