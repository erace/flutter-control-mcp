# Flutter Control

## Workflow
**User runs commands on host Mac only. Claude runs everything else in VM.**
- When deployment is needed: Claude starts HTTP server, user runs `curl ... | bash` on host
- Claude handles: code changes, starting servers in VM, testing from VM, documentation
- User handles: running install/update scripts on host Mac

---

Semantic UI automation for Flutter apps via MCP. Hybrid approach using:
- **Maestro** (Phase 1): Accessibility-layer automation, works on any app
- **Flutter Driver** (Phase 2): Widget-tree access for deeper inspection

**Architecture:**
- **Android** (on Host Mac):
  - VM → HTTP → Host MCP Server (port 9225) → Maestro/Driver → Android Emulator
  - Driver uses ADB port forwarding for VM Service access
- **iOS** (on VM):
  - VM → VM MCP Server (port 9226) → Maestro/Driver → iOS Simulator
  - Driver connects directly to VM Service (no port forwarding needed)

## Deploy/Update

**Host Mac (Android):**
```bash
# Fresh install
curl -sS http://192.168.64.100:9999/install.sh | bash

# Update
curl -sS http://192.168.64.100:9999/update-host.sh | bash
```

**VM (iOS):**
```bash
# Start VM MCP server for iOS
./scripts/start-vm-server.sh

# Or manually:
cd ~/Projects/pl.erace.claude.flutter.control
.venv/bin/python -c "import sys; sys.path.insert(0,'.'); from flutter_control.mcp.server import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=9226)"
```

## MCP Tools

### Unified API (Phase 3) - Auto-selects backend

| Tool | Description |
|------|-------------|
| `flutter_tap` | **Unified**: auto-selects Maestro or Driver based on finder |
| `flutter_assert_visible` | **Unified**: auto-selects backend |

**Finder → Backend:**
- `{text: "..."}`, `{id: "..."}` → Maestro (with Driver fallback for text)
- `{key: "..."}`, `{type: "..."}` → Driver only
- Add `backend: "maestro"` or `"driver"` to force

### Phase 1: Maestro-only tools

| Tool | Description |
|------|-------------|
| `flutter_double_tap` | Double tap element |
| `flutter_long_press` | Long press element |
| `flutter_swipe` | Swipe: up, down, left, right |
| `flutter_enter_text` | Enter text (optionally tap element first) |
| `flutter_clear_text` | Clear current text field |
| `flutter_assert_not_visible` | Assert element not visible |
| `flutter_screenshot` | Take screenshot (Maestro) |
| `flutter_screenshot_adb` | Take screenshot (ADB, 70x faster) |
| `flutter_debug_traces` | Get recent trace logs |
| `flutter_debug_trace` | Get specific trace by ID |

### Phase 2: Flutter Driver (widget tree)

| Tool | Description |
|------|-------------|
| `flutter_driver_discover` | Auto-discover VM service URI + setup port forwarding |
| `flutter_driver_connect` | Connect to Observatory/VM Service |
| `flutter_driver_disconnect` | Disconnect from Observatory |
| `flutter_driver_tap` | Tap by `{key: '...'}` or `{type: '...'}` |
| `flutter_get_text` | Get text from widget by key/type |
| `flutter_widget_tree` | Get render tree (JSON) |
| `flutter_run` | Launch app with Observatory enabled |

**Typical workflow:**
```
1. flutter_driver_discover  -> returns URI with auth token
2. flutter_driver_connect   -> pass the URI
3. flutter_driver_tap/flutter_get_text/etc.
```

## Testing Endpoints

**Android (Host - port 9225):**
```bash
# Health check
curl http://localhost:9225/health

# List tools
curl -H "Authorization: Bearer $(cat ~/.android-mcp-token)" http://localhost:9225/tools

# Call tool
curl -X POST http://localhost:9225/call \
  -H "Authorization: Bearer $(cat ~/.android-mcp-token)" \
  -H "Content-Type: application/json" \
  -d '{"name": "flutter_tap", "arguments": {"finder": {"text": "Increment"}}}'
```

**iOS (VM - port 9226):**
```bash
# Health check
curl http://localhost:9226/health

# Call tool (same API, different port)
curl -X POST http://localhost:9226/call \
  -H "Authorization: Bearer $(cat ~/.android-mcp-token)" \
  -H "Content-Type: application/json" \
  -d '{"name": "flutter_tap", "arguments": {"finder": {"text": "Increment"}}}'

# Flutter Driver on iOS (connect first)
curl -X POST http://localhost:9226/call \
  -H "Authorization: Bearer $(cat ~/.android-mcp-token)" \
  -H "Content-Type: application/json" \
  -d '{"name": "flutter_driver_connect", "arguments": {"uri": "http://127.0.0.1:<port>/<token>/"}}'
```

## Paths

**Host Mac (Android):**
- Server: `/usr/local/opt/flutter_control/`
- Logs: `~/Library/Logs/flutter-control/`
- Maestro flows: `~/Library/Logs/flutter-control/maestro/`

**VM (iOS):**
- Server: `~/Projects/pl.erace.claude.flutter.control/`
- Logs: `~/Library/Logs/flutter-control/vm-server.log`
- Venv: `~/Projects/pl.erace.claude.flutter.control/.venv/`
- Maestro: `~/.maestro/bin/maestro`

**Shared:**
- Token: `~/.android-mcp-token`

## Development

**Host Mac (Android - port 9225):**
```bash
# Restart service
launchctl kickstart -k gui/$(id -u)/com.flutter.control

# View logs
tail -f ~/Library/Logs/flutter-control/stderr.log
```

**VM (iOS - port 9226):**
```bash
# Restart service
launchctl kickstart -k gui/$(id -u)/com.flutter.control.ios

# View logs
tail -f ~/Library/Logs/flutter-control/vm-stderr.log

# Stop/Start manually
launchctl stop com.flutter.control.ios
launchctl start com.flutter.control.ios
```

**Common:**
```bash
# View generated Maestro flows
ls ~/Library/Logs/flutter-control/maestro/
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Element not found | Uses partial matching (regex), check text substring |
| Maestro not installed | Run: `curl -Ls 'https://get.maestro.mobile.dev' \| bash` |
| App not running | Start app on emulator first |
| Timeout | Increase timeout parameter or check element visibility |
| Screenshot slow | Maestro ~15s; ADB direct is 70x faster (220ms) |

## Project Status

See `PROJECT_STATUS.md` for:
- Implementation status vs plan
- Deviations from original plan
- Benchmark results
- Known issues
- Next steps

## Key Implementation Notes

### Maestro (Phase 1)
- **Finders**: Use `{text: '...'}` for labels, `{id: '...'}` for input fields
- **Assertions**: Use partial matching by default (`.*text.*` regex)
- **Screenshots**: Saved to `~/Library/Logs/flutter-control/screenshots/`
- **App ID**: Default is `com.example.flutter_control_test_app` (configurable)

### Flutter Driver (Phase 2)
- **Finders**: Use `{key: '...'}` for widget Keys, `{type: '...'}` for widget types
- **Requirements**: App must have `enableFlutterDriverExtension()` in main.dart
- **Observatory**: Default port 9223 (Android), 9224 (iOS)
- **Connection**: Call `flutter_driver_connect` before using driver tools

### Screenshots
- **Maestro**: ~15s per screenshot (full Maestro overhead)
- **ADB**: ~220ms per screenshot (70x faster, Android only)
  ```bash
  adb exec-out screencap -p > screenshot.png
  ```

### iOS (Phase 4)
- **Server**: VM MCP server on port 9226 (same codebase as host)
- **Maestro**: Installed on VM, connects directly to iOS Simulator
- **Flutter Driver**: Connects directly to VM Service (no port forwarding)
- **Start server**: `./scripts/start-vm-server.sh`
- **Logs**: `~/Library/Logs/flutter-control/vm-server.log`

### iOS Flutter Driver Workflow
```bash
# 1. Start app with flutter run
flutter run -d "iPhone 16e" --debug

# 2. Note the VM service URI from output:
#    "A Dart VM Service on iPhone 16e is available at: http://127.0.0.1:51504/abc=/"

# 3. Connect via MCP
flutter_driver_connect {uri: "http://127.0.0.1:51504/abc=/"}

# 4. Use driver tools
flutter_get_text {key: "count_label"}
flutter_driver_tap {key: "increment_btn"}
```

### Hot Reload (Phase 5)

**iOS:** Works directly - `flutter run` from VM connects to local VM Service.

**Android:** Uses Observatory relay chain:
```
VM:9223 (relay) → Host:9233 (bridge) → Host:9223 (ADB fwd) → Emulator
```

**Setup (automatic via LaunchAgents):**
- VM: `~/.android-mcp/observatory-relay.py` (port 9223)
- Host: `observatory-bridge.py` (port 9233)

**Manual restart:**
```bash
# VM relay
launchctl kickstart -k gui/$(id -u)/com.android.observatory-relay

# Host bridge
launchctl kickstart -k gui/$(id -u)/com.flutter.observatory-bridge
```
