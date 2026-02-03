# Flutter Control MCP

MCP server for Flutter app automation on iOS simulators and Android emulators.

## Overview

Flutter Control provides a unified API for automating Flutter apps using two backends:

| Backend | How it works | Best for |
|---------|--------------|----------|
| **Maestro** | Accessibility layer | Any app, text/id finders |
| **Flutter Driver** | Widget tree access | Apps with driver extension, key/type finders |

The server auto-selects the right backend based on your finder type.

## Architecture

```
┌─── VM (claude-dev.local) ───┐      ┌─── Host Mac (phost.local) ───┐
│                             │      │                               │
│  iOS MCP Server (:9226)     │      │  Android MCP Server (:9225)   │
│         ↓                   │      │         ↓                     │
│  iOS Simulator              │      │  Android Emulator             │
└─────────────────────────────┘      └───────────────────────────────┘
```

- **iOS**: Server runs on the same machine as simulator (VM)
- **Android**: Server runs on host Mac with emulator, accessed from VM

## Installation

### Quick Start (uvx - recommended)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run directly with uvx (no install needed)
uvx flutter-control-mcp
```

### MCP Client Configuration

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

### HTTP Server Installation

The MCP stdio client connects to an HTTP server that must be running:

```bash
# Install via pip
pip install git+https://github.com/erace/flutter-control-mcp.git

# Install as macOS service (auto-starts on boot)
flutter-control-install --port 9225  # Android (host Mac)
flutter-control-install --port 9226  # iOS (VM)

# Or run directly for development
flutter-control-server
```

### Requirements

- Python 3.11+
- macOS
- [uv](https://github.com/astral-sh/uv): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Maestro](https://maestro.mobile.dev/): `curl -Ls "https://get.maestro.mobile.dev" | bash`
- Android SDK (for Android)
- Xcode (for iOS)

## Flutter App Setup

To use Flutter Driver backend, add driver extension to your app:

**main.dart:**
```dart
import 'package:flutter_driver/driver_extension.dart';

void main() {
  // Enable driver in debug builds only (zero overhead in release)
  assert(() {
    enableFlutterDriverExtension();
    return true;
  }());
  runApp(const MyApp());
}
```

**pubspec.yaml:**
```yaml
dev_dependencies:
  flutter_driver:
    sdk: flutter
```

**Add keys to widgets for automation:**
```dart
ElevatedButton(
  key: const Key('submit_btn'),  // For {key: "submit_btn"}
  onPressed: _onSubmit,
  child: const Text('Submit'),   // For {text: "Submit"}
)
```

## Discovery

Flutter Control uses **mDNS** (Bonjour) to discover the Flutter VM Service - the same mechanism Flutter tooling uses. When your app launches with driver extension enabled, it advertises via `_dartVmService._tcp`. The server discovers this automatically.

No need to run `flutter run` or manually find ports. Just:
1. Install your debug app
2. Launch it
3. Call MCP tools

Fallbacks: logcat parsing (Android), port scanning (iOS).

## API Usage

### Endpoints

```bash
# Health check
curl http://localhost:9225/health

# Version info
curl http://localhost:9225/version

# List tools
curl http://localhost:9225/tools

# Call a tool
curl -X POST http://localhost:9225/call \
  -H "Authorization: Bearer $(cat ~/.android-mcp-token)" \
  -H "Content-Type: application/json" \
  -d '{"name": "flutter_tap", "arguments": {"finder": {"text": "Submit"}}}'
```

### Finder Types

| Finder | Backend | Example | Notes |
|--------|---------|---------|-------|
| `{text: "..."}` | Maestro | `{"text": "Submit"}` | Partial match |
| `{id: "..."}` | Maestro | `{"id": "btn_submit"}` | Android resource ID |
| `{key: "..."}` | Driver | `{"key": "submit_btn"}` | Widget ValueKey |
| `{type: "..."}` | Driver | `{"type": "TextButton"}` | Must be unique |

Force a specific backend: `{"text": "Submit", "backend": "maestro"}`

## MCP Tools (25)

### UI Interactions (6)

| Tool | Description |
|------|-------------|
| `flutter_tap` | Tap element |
| `flutter_double_tap` | Double tap element |
| `flutter_long_press` | Long press element |
| `flutter_swipe` | Swipe direction (up/down/left/right) |
| `flutter_enter_text` | Type text into field |
| `flutter_clear_text` | Clear current text field |

### Assertions (2)

| Tool | Description |
|------|-------------|
| `flutter_assert_visible` | Assert element is visible |
| `flutter_assert_not_visible` | Assert element is not visible |

### Screenshots (2)

| Tool | Description |
|------|-------------|
| `flutter_screenshot` | Smart: ADB (Android) / simctl (iOS), Maestro fallback |
| `flutter_screenshot_maestro` | Explicit Maestro screenshot |

### Flutter Driver (7)

| Tool | Description |
|------|-------------|
| `flutter_driver_discover` | Find VM Service URI via mDNS |
| `flutter_driver_connect` | Connect to VM Service |
| `flutter_driver_disconnect` | Disconnect |
| `flutter_driver_tap` | Tap via Driver (key/type finders) |
| `flutter_get_text` | Get text from widget |
| `flutter_widget_tree` | Dump render tree |
| `flutter_run` | Launch app with Observatory |

### iOS Lifecycle (3)

| Tool | Description |
|------|-------------|
| `ios_list_devices` | List available simulators |
| `ios_boot_simulator` | Boot simulator by name or UDID |
| `ios_shutdown_simulator` | Shutdown simulator |

### Android Lifecycle (3)

| Tool | Description |
|------|-------------|
| `android_list_devices` | List emulators, devices, and AVDs |
| `android_boot_emulator` | Boot emulator by AVD name |
| `android_shutdown_emulator` | Shutdown emulator |

### Debug (2)

| Tool | Description |
|------|-------------|
| `flutter_version` | Server version and info |
| `flutter_debug_trace` | Get trace(s) - by ID or recent |

## Examples

```bash
# Tap button by text
curl -X POST http://localhost:9225/call \
  -d '{"name": "flutter_tap", "arguments": {"finder": {"text": "Increment"}}}'

# Tap by widget key
curl -X POST http://localhost:9225/call \
  -d '{"name": "flutter_tap", "arguments": {"finder": {"key": "increment_btn"}}}'

# Get counter value
curl -X POST http://localhost:9225/call \
  -d '{"name": "flutter_get_text", "arguments": {"finder": {"key": "counter_label"}}}'

# Assert text visible
curl -X POST http://localhost:9225/call \
  -d '{"name": "flutter_assert_visible", "arguments": {"finder": {"text": "Welcome"}}}'

# Take screenshot (auto-selects fastest method)
curl -X POST http://localhost:9225/call \
  -d '{"name": "flutter_screenshot", "arguments": {}}'

# Swipe down
curl -X POST http://localhost:9225/call \
  -d '{"name": "flutter_swipe", "arguments": {"direction": "down"}}'

# List Android devices
curl -X POST http://localhost:9225/call \
  -d '{"name": "android_list_devices", "arguments": {}}'

# Boot iOS simulator
curl -X POST http://localhost:9226/call \
  -d '{"name": "ios_boot_simulator", "arguments": {"device_name": "iPhone 16"}}'
```

## Development

```bash
# Clone
git clone https://github.com/erace/flutter-control-mcp.git
cd flutter-control-mcp

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests (defaults use mDNS hostnames)
TEST_PLATFORM=ios pytest tests/ -v      # iOS
TEST_PLATFORM=android pytest tests/ -v  # Android

# Custom host (e.g., remote server)
ANDROID_HOST=farm-01.local TEST_PLATFORM=android pytest tests/ -v

# Serve for host updates
python3 -m http.server 9999
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Element not found | Text uses partial match - check substring |
| Driver 403 Forbidden | Auth token missing - use `flutter_driver_discover` |
| Too many elements | Type finder matched multiple - use key instead |
| Maestro not installed | `curl -Ls "https://get.maestro.mobile.dev" \| bash` |
| mDNS not working | Falls back to logcat (Android) or port scan (iOS) |

## License

MIT
