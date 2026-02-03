# Configuration Reference

## Environment Variables

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FLUTTER_CONTROL_PORT` | `9225` | HTTP server port |
| `FLUTTER_CONTROL_HOST` | `0.0.0.0` | HTTP server bind address |
| `FLUTTER_CONTROL_TOKEN` | (from file) | Auth token (overrides file) |

### MCP Client Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FLUTTER_CONTROL_HOST` | `phost.local` | Server to connect to |
| `FLUTTER_CONTROL_PORT` | `9225` | Server port |
| `FLUTTER_CONTROL_TOKEN` | (from file) | Auth token |

### Test Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_PLATFORM` | `android` | Platform to test: `android` or `ios` |
| `ANDROID_HOST` | `phost.local` | Host for all Android services |
| `FLUTTER_CONTROL_PORT` | `9225` | Flutter Control port |
| `BRIDGE_PORT` | `9222` | Android MCP Bridge port |
| `IOS_HOST` | `localhost` | iOS server host |
| `IOS_PORT` | `9226` | iOS server port |
| `IOS_DEVICE_NAME` | `iPhone 16e` | iOS simulator to use |
| `ANDROID_AVD_NAME` | `Pixel_7_API_35` | Android AVD to boot |
| `VM_SERVICE_URI` | (auto) | Override Flutter Driver URI |
| `TEST_DEVICE_ID` | (auto) | Specific device to test |

### ADB Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ADB_SERVER_SOCKET` | `tcp:phost.local:15037` | Remote ADB server |

## MCP Client Configuration

### Claude Code (`~/.claude/mcp_servers.json`)

Since the package isn't on PyPI yet, use `uvx --from git+...`:

```json
{
  "mcpServers": {
    "flutter-control-android": {
      "command": "/Users/admin/.local/bin/uvx",
      "args": ["--from", "git+https://github.com/erace/flutter-control-mcp.git", "flutter-control-mcp"],
      "env": {
        "FLUTTER_CONTROL_HOST": "phost.local",
        "FLUTTER_CONTROL_PORT": "9225"
      }
    },
    "flutter-control-ios": {
      "command": "/Users/admin/.local/bin/uvx",
      "args": ["--from", "git+https://github.com/erace/flutter-control-mcp.git", "flutter-control-mcp"],
      "env": {
        "FLUTTER_CONTROL_HOST": "localhost",
        "FLUTTER_CONTROL_PORT": "9226"
      }
    },
    "android-bridge": {
      "command": "python3",
      "args": ["/path/to/android-mcp-bridge/android-mcp-stdio.py"],
      "env": {
        "ANDROID_MCP_URL": "http://phost.local:9222"
      }
    }
  }
}
```

### When published to PyPI (future)

```json
{
  "mcpServers": {
    "flutter-control": {
      "command": "uvx",
      "args": ["flutter-control-mcp"],
      "env": {
        "FLUTTER_CONTROL_HOST": "phost.local"
      }
    }
  }
}
```

## macOS LaunchAgent

Service definition at `~/Library/LaunchAgents/com.erace.flutter-control.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.erace.flutter-control</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python3</string>
        <string>-m</string>
        <string>flutter_control.mcp.server</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>FLUTTER_CONTROL_PORT</key>
        <string>9225</string>
        <key>FLUTTER_CONTROL_HOST</key>
        <string>0.0.0.0</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:~/.maestro/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>~/Library/Logs/flutter-control/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>~/Library/Logs/flutter-control/stderr.log</string>
</dict>
</plist>
```

## Port Reference

| Port | Service | Location |
|------|---------|----------|
| 9222 | Android MCP Bridge | Host Mac |
| 9225 | Flutter Control (Android) | Host Mac |
| 9226 | Flutter Control (iOS) | VM |
| 9223 | Observatory relay | VM |
| 9233 | Observatory bridge | Host Mac |
| 15037 | ADB proxy | Host Mac |

## Shell Configuration (`~/.zshrc`)

Recommended minimal configuration:

```bash
# Flutter Control - single host for all Android services
export ANDROID_HOST=phost.local

# Auth token (shared with android-mcp-bridge)
export ANDROID_MCP_TOKEN=$(cat ~/.android-mcp-token 2>/dev/null)

# Android SDK (for adb)
export PATH="$PATH:$HOME/Library/Android/sdk/platform-tools"

# Maestro
export PATH="$PATH:$HOME/.maestro/bin"
```

## Deprecated Variables

These are no longer used (replaced by `ANDROID_HOST`):

| Old Variable | Replacement |
|--------------|-------------|
| `ANDROID_MCP_HOST` | `ANDROID_HOST` |
| `ANDROID_MCP_PORT` | `FLUTTER_CONTROL_PORT` |
| `ANDROID_MCP_BRIDGE_HOST` | `ANDROID_HOST` |
| `ANDROID_MCP_BRIDGE_PORT` | `BRIDGE_PORT` |

If these are set, you'll see deprecation warnings during test runs.
