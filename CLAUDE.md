# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workflow

**User runs commands on host Mac only. Claude runs everything else in VM.**
- Deployment: Claude starts HTTP server (`python3 -m http.server 9999`), user runs `curl ... | bash` on host
- Claude handles: code changes, starting VM servers, testing, documentation
- User handles: running install/update scripts on host Mac

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ VM (Claude Code)                                            │
│                                                              │
│  iOS MCP Server (port 9226) ─────→ iOS Simulator            │
│  Observatory Relay (port 9223) ───┐                         │
└───────────────────────────────────│─────────────────────────┘
                                    │ HTTP/TCP
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│ Host Mac                                                     │
│                                                              │
│  Android MCP Server (port 9225) ──→ Android Emulator        │
│  Observatory Bridge (port 9233) ──→ ADB forward:9223        │
└─────────────────────────────────────────────────────────────┘
```

**Two backends:**
- **Maestro**: Accessibility-layer automation, works on any app, uses text/id finders
- **Flutter Driver**: Widget-tree access, requires driver extension enabled, uses key/type finders

**MCP role:** Control plane only. MCP tools manage the proxy and emulator; actual ADB traffic flows directly over TCP.

## Mobile App Automation Pattern

**This is the standard pattern for all Flutter projects to enable automation testing.**

### App Setup (Required for Driver backend)

Add this to your app's `main.dart`:

```dart
import 'package:flutter_driver/driver_extension.dart';

void main() {
  // Auto-enable Flutter Driver in debug builds only.
  // Zero overhead in release builds (tree-shaken out).
  assert(() {
    enableFlutterDriverExtension();
    return true;
  }());

  runApp(const MyApp());
}
```

Also add to `pubspec.yaml`:
```yaml
dev_dependencies:
  flutter_driver:
    sdk: flutter
```

### Build Types

| Build | Driver Enabled | Use Case |
|-------|----------------|----------|
| `flutter run` | Yes | Development + testing |
| `flutter build --debug` | Yes | CI/automation testing |
| `flutter build --release` | No | Production (zero overhead) |

### Widget Keys for Automation

Add `Key` to widgets you want to interact with programmatically:

```dart
ElevatedButton(
  key: const Key('submit_btn'),  // For flutter_tap {key: "submit_btn"}
  onPressed: _onSubmit,
  child: const Text('Submit'),   // For flutter_tap {text: "Submit"}
)

Text(
  '$_counter',
  key: const Key('count_label'), // For flutter_get_text {key: "count_label"}
)
```

### Bootstrap Sequence

When tests run, bootstrap automatically:
1. Starts emulator/simulator if needed
2. Installs debug app
3. Launches app
4. Connects to Observatory (enables Driver backend)

All backends (Maestro + Driver) are then available for automation.

## Deploy/Update

**Host Mac (Android):**
```bash
curl -sS http://192.168.64.100:9999/scripts/install.sh | bash      # Fresh install
curl -sS http://192.168.64.100:9999/scripts/update-host.sh | bash  # Update
```

**VM (iOS):**
```bash
./scripts/start-vm-server.sh
```

## Development Commands

```bash
# Restart services
launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control.android  # Host
launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control.ios      # VM

# View logs
tail -f ~/Library/Logs/flutter-control/stderr.log     # Host
tail -f ~/Library/Logs/flutter-control/vm-stderr.log  # VM

# Test endpoints
curl http://localhost:9225/health  # Android
curl http://localhost:9226/health  # iOS

# Call tool
curl -X POST http://localhost:9225/call \
  -H "Authorization: Bearer $(cat ~/.android-mcp-token)" \
  -H "Content-Type: application/json" \
  -d '{"name": "flutter_tap", "arguments": {"finder": {"text": "Increment"}}}'
```

## Key Source Structure

```
flutter_control/
├── config.py              # Ports, timeouts, paths (env vars: FLUTTER_CONTROL_*)
├── logging/trace.py       # TraceContext for debugging
├── maestro/
│   ├── wrapper.py         # CLI wrapper - executes Maestro
│   ├── flow_builder.py    # Generates YAML flows
│   └── parser.py          # Parses Maestro output
├── driver/
│   ├── client.py          # WebSocket client to Observatory
│   ├── protocol.py        # JSON-RPC protocol
│   ├── finders.py         # ByKey, ByType, ByText, etc.
│   └── commands.py        # High-level driver commands
├── unified/
│   ├── backend_selector.py  # Auto-select based on finder type
│   └── executor.py          # Execute with fallback
└── mcp/
    ├── server.py          # FastAPI endpoints (/health, /call, /tools)
    └── tools.py           # 17+ MCP tool definitions and handlers
```

## Backend Selection

| Finder | Primary | Fallback | Notes |
|--------|---------|----------|-------|
| `{text: "..."}` | Maestro | Driver | Accessibility layer |
| `{id: "..."}` | Maestro | none | Android resource ID |
| `{key: "..."}` | Driver | none | Widget ValueKey |
| `{type: "..."}` | Driver | none | Widget type name |

Force backend: add `backend: "maestro"` or `"driver"` to finder.

## Flutter Driver Workflow

```bash
# 1. Discover VM service (sets up port forwarding)
flutter_driver_discover

# 2. Connect (pass the URI from discover)
flutter_driver_connect {uri: "http://127.0.0.1:9223/abc=/"}

# 3. Use driver tools
flutter_get_text {key: "count_label"}
flutter_driver_tap {key: "increment_btn"}
```

**Critical:** VM Service URL includes auth token path (`/abc=/`). The `flutter_driver_discover` tool extracts this automatically.

## Hot Reload (Phase 5)

**iOS:** Direct - `flutter run` from VM connects to local VM Service.

**Android:** Relay chain:
```
VM:9223 (relay) → Host:9233 (bridge) → Host:9223 (ADB fwd) → Emulator
```

## Paths

| Path | Purpose |
|------|---------|
| `~/.android-mcp-token` | Bearer token (shared with android-mcp-bridge) |
| `~/Library/Logs/flutter-control/` | Server logs, traces, screenshots |
| `/usr/local/opt/flutter_control/` | Host installation |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Element not found | Uses partial matching (regex `.*text.*`), check text substring |
| Maestro not installed | `curl -Ls 'https://get.maestro.mobile.dev' \| bash` |
| Screenshot slow | Maestro ~15s; use `flutter_screenshot_adb` (220ms) |
| Driver 403 Forbidden | Auth token missing from URI - use `flutter_driver_discover` |
| Too many elements (Driver) | Type finder `{type: "..."}` matched multiple widgets; use unique type or key finder |

## Finder Best Practices

- **Prefer key finders** (`{key: "..."}`) for reliable, unambiguous targeting
- **Type finders** (`{type: "..."}`) only work when exactly one widget matches - use unique types like `TextButton` not `ElevatedButton` or `Text`
- **Text finders** (`{text: "..."}`) use partial matching - "Submit" matches "Submit Order"
- For `flutter_get_text`, always use key finders since type finders often match multiple Text widgets

## Test App

Located in `test_app/`. Uses the standard automation pattern with debug-only driver extension.

```bash
# Build and deploy from VM
export PATH="$PATH:/Users/admin/Library/Android/sdk/platform-tools"
cd test_app && flutter build apk --debug
adb install -r build/app/outputs/flutter-apk/app-debug.apk
adb shell am start -n com.example.flutter_control_test_app/.MainActivity
```

## Integration Tests

Located in `tests/`. Tests call the HTTP server directly (not through MCP protocol).

Bootstrap automatically:
- Starts emulator/simulator if needed
- Installs and launches test app
- Connects to Flutter Driver Observatory

```bash
source .venv/bin/activate
export PATH="$PATH:/Users/admin/Library/Android/sdk/platform-tools"

# Run Android tests (FROM VM - note host IP!)
TEST_PLATFORM=android ANDROID_MCP_HOST=192.168.64.1 ANDROID_MCP_PORT=9225 \
  ANDROID_MCP_BRIDGE_HOST=192.168.64.1 ANDROID_MCP_BRIDGE_PORT=9222 \
  pytest tests/ -v

# Run iOS tests
TEST_PLATFORM=ios IOS_MCP_PORT=9226 \
  pytest tests/ -v

# Run single test
pytest tests/test_tap.py::TestTapByText -v

# Run by marker
pytest tests/ -m "maestro_only" -v
pytest tests/ -m "driver_only" -v
pytest tests/ -m "slow" -v
```

**Markers:** `slow`, `driver_only`, `maestro_only`, `android_only`, `ios_only`

## Test Progress Display

When showing test results, use this format:

```
Test Progress                        37/49  75%
────────────────────────────────────────────────
Tap by text          ██████████  6/6
Tap by widget key    ░░░░░░░░░░  0/2   ✗
Tap by widget type   ░░░░░░░░░░  0/2   ✗
Tap by resource ID   ██████████  1/1
Assert visible       ██████████  8/8
Assert not visible   ████████░░  3/4
Get text from widget ███████░░░  2/3
Swipe gestures       ██████████  4/4
Double tap           █████░░░░░  1/2
Long press           █████░░░░░  1/2
Screenshots          ██████████  4/4
Text input           ██████████  4/4
Driver connection    ██████████  4/4
Widget tree          ██████████  1/1
────────────────────────────────────────────────
Needs Fix:
  • Category → Root cause
```

Format rules:
- Feature names padded to 20 chars for alignment
- Progress bar: 10 chars (`█` = passed, `░` = failed)
- Ratio: passed/total
- `✗` suffix for completely broken (0 passed)
- Group failures by root cause at bottom
