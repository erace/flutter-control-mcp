# Installation Guide

## Prerequisites

- **macOS** (Intel or Apple Silicon)
- **Python 3.11+**
- **uv** (recommended) or pip

### Install uv (Python package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Maestro (UI automation)

```bash
curl -Ls "https://get.maestro.mobile.dev" | bash
```

### Platform-specific

**Android:**
- Android SDK with platform-tools (adb)
- Android Emulator with at least one AVD

**iOS:**
- Xcode with Command Line Tools
- iOS Simulator

## Quick Start (uvx)

The simplest way to use Flutter Control is with uvx - no installation needed:

```bash
# Run directly (from GitHub, not on PyPI yet)
uvx --from git+https://github.com/erace/flutter-control-mcp.git flutter-control-mcp

# With specific server
FLUTTER_CONTROL_HOST=phost.local uvx --from git+https://github.com/erace/flutter-control-mcp.git flutter-control-mcp

# When published to PyPI (future):
# uvx flutter-control-mcp
```

## Full Installation

### Step 1: Install the package

```bash
# Option A: From GitHub (recommended)
pip install git+https://github.com/erace/flutter-control-mcp.git

# Option B: From PyPI (when published)
pip install flutter-control-mcp

# Option C: Development install
git clone https://github.com/erace/flutter-control-mcp.git
cd flutter-control-mcp
pip install -e ".[dev]"
```

### Step 2: Install as macOS service

```bash
# Android server (on host Mac)
flutter-control-install --port 9225

# iOS server (on VM)
flutter-control-install --port 9226
```

This creates a LaunchAgent that:
- Starts automatically on boot
- Restarts on crash
- Logs to `~/Library/Logs/flutter-control/`

### Step 3: Configure MCP client

Add to `~/.claude/mcp_servers.json`:

```json
{
  "mcpServers": {
    "flutter-control-android": {
      "command": "uvx",
      "args": ["flutter-control-mcp"],
      "env": {
        "FLUTTER_CONTROL_HOST": "phost.local",
        "FLUTTER_CONTROL_PORT": "9225"
      }
    },
    "flutter-control-ios": {
      "command": "uvx",
      "args": ["flutter-control-mcp"],
      "env": {
        "FLUTTER_CONTROL_HOST": "localhost",
        "FLUTTER_CONTROL_PORT": "9226"
      }
    }
  }
}
```

### Step 4: Verify

```bash
# Check server health
curl http://localhost:9225/health

# Check version
curl http://localhost:9225/version

# List tools
curl http://localhost:9225/tools
```

## VM + Host Mac Setup

For the typical development setup with VM running Claude Code and host Mac running Android:

### On Host Mac

```bash
# 1. Install
pip install git+https://github.com/erace/flutter-control-mcp.git

# 2. Install as service
flutter-control-install --port 9225

# 3. Verify from VM
curl http://phost.local:9225/health
```

### On VM

```bash
# 1. Install
pip install git+https://github.com/erace/flutter-control-mcp.git

# 2. Install as service (iOS)
flutter-control-install --port 9226

# 3. Configure MCP client (see above)
```

## Updating

### Via pip (from source on VM)

```bash
# On VM: Start HTTP server
cd flutter-control-mcp
python3 -m http.server 9999 &

# Build wheel
pip install build
python -m build --wheel

# On Host Mac: Update
curl -sS http://claude-dev.local:9999/update.sh | bash
```

### Via pip (from GitHub)

```bash
pip install --upgrade git+https://github.com/erace/flutter-control-mcp.git
launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control
```

## Uninstalling

```bash
# Uninstall service
flutter-control-install --uninstall

# Uninstall package
pip uninstall flutter-control-mcp

# Clean up (optional)
rm -rf ~/Library/Logs/flutter-control/
rm ~/.android-mcp-token  # if not shared with other tools
```

## Troubleshooting

### Service won't start

Check logs:
```bash
tail -f ~/Library/Logs/flutter-control/stderr.log
```

### Port already in use

```bash
# Find what's using the port
lsof -i :9225

# Kill it
kill $(lsof -ti :9225)

# Restart service
launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control
```

### Maestro not found

Ensure Maestro is in PATH:
```bash
export PATH="$PATH:$HOME/.maestro/bin"
```

Or reinstall:
```bash
curl -Ls "https://get.maestro.mobile.dev" | bash
```

### Can't connect from VM to Host

Check mDNS resolution:
```bash
ping phost.local
```

If it fails, check Bonjour is enabled on both machines.
