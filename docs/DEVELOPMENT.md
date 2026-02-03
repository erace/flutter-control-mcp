# Development Guide

## Project Structure

```
flutter-control-mcp/
├── flutter_control/           # Main package
│   ├── __init__.py
│   ├── __version__.py         # Single source of truth for version
│   ├── cli.py                 # CLI commands and MCP stdio server
│   ├── config.py              # Configuration and defaults
│   ├── logging/
│   │   └── trace.py           # TraceContext for debugging
│   ├── maestro/
│   │   ├── wrapper.py         # Maestro CLI wrapper
│   │   ├── flow_builder.py    # YAML flow generation
│   │   └── parser.py          # Output parsing
│   ├── driver/
│   │   ├── client.py          # WebSocket client
│   │   ├── protocol.py        # JSON-RPC protocol
│   │   ├── finders.py         # ByKey, ByType, ByText
│   │   └── commands.py        # High-level commands
│   ├── unified/
│   │   ├── backend_selector.py # Auto-select based on finder
│   │   └── executor.py         # Execute with fallback
│   └── mcp/
│       ├── server.py          # FastAPI HTTP server
│       └── tools.py           # MCP tool definitions
├── tests/
│   ├── conftest.py            # Pytest fixtures
│   ├── fixtures/
│   │   ├── bootstrap.py       # Test environment setup
│   │   ├── platform.py        # Platform config
│   │   └── mcp_client.py      # HTTP client for tests
│   └── test_*.py              # Test files
├── test_app/                  # Flutter test app
├── scripts/
│   └── release.sh             # Version release script
├── docs/                      # Documentation
├── pyproject.toml             # Package metadata
├── update.sh                  # Host update script
└── CHANGELOG.md               # Release notes
```

## Setting Up Development Environment

```bash
# Clone
git clone https://github.com/erace/flutter-control-mcp.git
cd flutter-control-mcp

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Verify
python -c "from flutter_control import __version__; print(__version__)"
```

## Running the Server

```bash
# Development mode (auto-reload would need uvicorn --reload)
FLUTTER_CONTROL_PORT=9226 python -m flutter_control.mcp.server

# Or via CLI
flutter-control-server
```

## Running Tests

```bash
# iOS tests (from VM)
TEST_PLATFORM=ios pytest tests/ -v

# Android tests (from VM, requires host Mac running)
TEST_PLATFORM=android pytest tests/ -v

# Single test
pytest tests/test_tap.py::TestTapByText -v

# With markers
pytest tests/ -m "maestro_only" -v
pytest tests/ -m "driver_only" -v
pytest tests/ -m "slow" -v
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `slow` | Tests that take longer |
| `driver_only` | Requires Flutter Driver |
| `maestro_only` | Uses only Maestro |
| `android_only` | Android-specific |
| `ios_only` | iOS-specific |

## Building Wheels

```bash
# Install build tool
pip install build

# Build wheel
python -m build --wheel

# Wheel is in dist/
ls dist/*.whl
```

## Release Process

### 1. Update version

Edit these files (or use release.sh):
- `flutter_control/__version__.py`
- `pyproject.toml`

### 2. Update CHANGELOG.md

Add entry under `[Unreleased]`, then rename to version.

### 3. Commit and tag

```bash
git add -A
git commit -m "chore: release vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main --tags
```

### 4. Build and distribute

```bash
python -m build --wheel
# For host update, serve via HTTP server
python3 -m http.server 9999
```

## Adding a New MCP Tool

### 1. Define the tool in `mcp/tools.py`

```python
# Add to TOOLS list
{
    "name": "flutter_my_tool",
    "description": "Description for MCP clients",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
        },
        "required": ["param1"]
    }
}
```

### 2. Add handler in `handle_tool_call`

```python
elif name == "flutter_my_tool":
    param1 = args.get("param1")
    # Implementation
    return {"success": True, "result": "..."}
```

### 3. Add tests

Create `tests/test_my_tool.py`:

```python
import pytest

class TestMyTool:
    @pytest.mark.asyncio
    async def test_my_tool_basic(self, mcp_client):
        result = await mcp_client.call("flutter_my_tool", {"param1": "value"})
        assert result.get("success")
```

## Code Style

- Python 3.11+ features allowed
- Type hints for public APIs
- Docstrings for classes and public methods
- No unnecessary comments (code should be self-documenting)

## Debugging

### Enable trace logging

```python
from flutter_control.logging.trace import TraceContext

trace = TraceContext("my_operation")
trace.log("Starting...")
trace.log("Result", data=result)
```

### Get traces via API

```bash
curl -X POST http://localhost:9225/call \
  -H "Content-Type: application/json" \
  -d '{"name": "flutter_debug_trace", "arguments": {"count": 10}}'
```

### View server logs

```bash
tail -f ~/Library/Logs/flutter-control/stderr.log
```

## Testing on Real Devices

### Android

```bash
# List devices
adb devices

# Set device for tests
TEST_DEVICE_ID=emulator-5554 TEST_PLATFORM=android pytest tests/ -v
```

### iOS

```bash
# List simulators
xcrun simctl list devices

# Set device for tests
TEST_DEVICE_ID=<UDID> TEST_PLATFORM=ios pytest tests/ -v
```
