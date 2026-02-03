# Flutter Control - Project Status

**Last Updated:** 2026-01-31
**Current Phase:** Phase 6 Complete ✅

## Project Overview

Semantic UI automation for Flutter apps via MCP. Uses Maestro for reliable cross-platform automation.

**Architecture:** VM (Claude Code) → HTTP+Bearer Token → Host Mac (port 9225) → Maestro → Device

## Implementation Status vs Plan

### Phase 1: Maestro Backend - COMPLETE ✅

| Planned Tool | Status | Notes |
|--------------|--------|-------|
| `flutter_tap` | ✅ Done | Works with `text` and `id` finders |
| `flutter_double_tap` | ✅ Done | |
| `flutter_long_press` | ✅ Done | |
| `flutter_swipe` | ✅ Done | Fixed: uses `swipe` not `scroll` |
| `flutter_enter_text` | ✅ Done | Supports `id` finder for TextFields |
| `flutter_clear_text` | ✅ Done | |
| `flutter_assert_visible` | ✅ Done | Fixed: uses regex partial matching |
| `flutter_assert_not_visible` | ✅ Done | Fixed: uses regex partial matching |
| `flutter_screenshot` | ✅ Done | Fixed: absolute path, returns base64 |
| `flutter_debug_traces` | ✅ Done | |
| `flutter_debug_trace` | ✅ Done | |

**Phase 1 Exit Criteria:** All tools working - PASSED

### Phase 2: Flutter Driver Backend - COMPLETE ✅

| Planned Item | Status | Notes |
|--------------|--------|-------|
| Observatory WebSocket client | ✅ Done | `flutter_control/driver/client.py` |
| Flutter Driver protocol | ✅ Done | `flutter_control/driver/protocol.py` |
| Key/type finders | ✅ Done | ByKey, ByType, ByText, ByTooltip, BySemanticsLabel |
| Widget tree inspection | ✅ Done | `flutter_widget_tree` tool - tested, returns 614KB tree |
| `flutter_get_text` tool | ✅ Done | Tested: correctly returns widget text |
| `flutter_run` tool | ✅ Done | Launch with Observatory port |
| `flutter_driver_tap` tool | ✅ Done | Tested: counter 1→2 |
| `flutter_driver_discover` tool | ✅ Done | Auto-discovers VM service URI and sets up port forwarding |
| Test app driver extension | ✅ Done | `enableFlutterDriverExtension()` |

**Phase 2 Exit Criteria:** All tools tested and working ✅

### Phase 3: Unified API + Auto-Fallback - COMPLETE ✅

| Feature | Status | Notes |
|---------|--------|-------|
| Backend selector | ✅ Done | Auto-selects based on finder type |
| Auto-fallback | ✅ Done | Falls back if primary backend fails |
| Unified `flutter_tap` | ✅ Done | text/id → Maestro, key/type → Driver |
| Unified `flutter_assert_visible` | ✅ Done | Same auto-selection logic |
| Force backend option | ✅ Done | `backend: "maestro"` or `"driver"` |
| Trace logging with backend | ✅ Done | Response includes `backend`, `backends_tried` |

**Test Results:**
- `{text: "Increment"}` → Maestro ✅
- `{key: "increment_btn"}` → Driver ✅
- `{text: "...", backend: "driver"}` → Driver (forced) ✅
- Count: 4 → 6 after 3 taps (all backends worked)

### Phase 4: iOS Support - COMPLETE ✅

| Feature | Status | Notes |
|---------|--------|-------|
| Maestro on VM | ✅ Done | Installed via curl installer |
| VM MCP Server | ✅ Done | Port 9226, same codebase as host |
| iOS flutter_tap | ✅ Done | Via Maestro |
| iOS flutter_assert_visible | ✅ Done | Via Maestro |
| iOS flutter_screenshot | ✅ Done | Via Maestro |
| iOS flutter_driver_connect | ✅ Done | Direct to VM service (no port forwarding needed) |
| iOS flutter_driver_tap | ✅ Done | Via Flutter Driver |
| iOS flutter_get_text | ✅ Done | Via Flutter Driver |

**Architecture:**
```
iOS: VM → VM MCP Server (9226) → Maestro/Driver → iOS Simulator (on VM)
Android: VM → Host MCP Server (9225) → Maestro/Driver → Android Emulator (on Host)
```

**Key Insight:** iOS Simulator runs on VM, so VM MCP server connects directly to VM service (no port forwarding like Android)

**VM Server Auto-Start:**
- LaunchAgent: `~/Library/LaunchAgents/com.flutter.control.ios.plist`
- Starts automatically on VM boot
- Restart: `launchctl kickstart -k gui/$(id -u)/com.flutter.control.ios`
- Logs: `~/Library/Logs/flutter-control/vm-stderr.log`

### Phase 5: Observatory Relay (Hot Reload) - COMPLETE ✅

| Feature | Status | Notes |
|---------|--------|-------|
| VM Observatory Relay | ✅ Done | `~/.android-mcp/observatory-relay.py` (port 9223) |
| Host Observatory Bridge | ✅ Done | Exposes ADB forward on port 9233 |
| Android Hot Reload | ✅ Done | VM:9223 → Host:9233 → Host:9223 → Emulator |
| iOS Hot Reload | ✅ Done | Direct (no relay needed, VM Service on VM) |
| LaunchAgents | ✅ Done | Auto-start on boot for both |

**Architecture:**
```
Android: VM:9223 (relay) → Host:9233 (bridge) → Host:9223 (ADB fwd) → Emulator
iOS:     VM:9223 (direct) → iOS Simulator (on VM)
```

### Phase 6: Polish & Cleanup - COMPLETE ✅

| Feature | Status | Notes |
|---------|--------|-------|
| Service Cleanup | ✅ Done | Removed stale services, unified naming |
| New Naming Scheme | ✅ Done | `com.erace.flutter-control.*` |
| Wrapper Scripts | ✅ Done | Nice process names in Activity Monitor |
| Version Endpoint | ✅ Done | `/version` endpoint + `flutter_version` tool |
| VM Services | ✅ Done | Migrated to new naming |
| Host Services | ✅ Done | Deployed 2026-01-31 |

**Service Naming:**
- `com.erace.flutter-control.ios` - iOS MCP server (VM)
- `com.erace.flutter-control.android` - Android MCP server (Host)
- `com.erace.flutter-control.adb-relay` - ADB relay (VM)
- `com.erace.flutter-control.observatory-relay` - Observatory relay (VM)
- `com.erace.flutter-control.observatory-bridge` - Observatory bridge (Host)

**Removed Old Services:**
- `com.flutter.control.ios`
- `com.android.adb-relay`
- `com.android.observatory-relay`
- `com.android-mcp.fileserver`

## Problems Solved

### Phase 3 Issues

1. **Unified Executor Initialization**
   - **Problem:** Need to share driver client between unified executor and direct tools
   - **Solution:** Lazy initialization with `_get_unified_executor()` that reuses `_get_driver_client()`

2. **Backend Selection Logic**
   - **Challenge:** Determine which backend to use based on finder type
   - **Solution:** `BackendSelector` class with clear rules:
     - `text`, `id` → Maestro preferred (accessibility layer)
     - `key`, `type`, `tooltip` → Driver required (widget tree)
     - `text` can fall back to Driver if Maestro fails

3. **Fallback Order**
   - **Challenge:** Some finders work with both backends, some with only one
   - **Solution:** `get_fallback_order()` returns list of backends to try:
     - Driver-only finders: `[Driver]` (no fallback)
     - Maestro-only finders: `[Maestro]` (no fallback)
     - Both: `[Primary, Other]` based on finder type

### Phase 2 Issues

1. **WebSocket 403 Forbidden**
   - **Problem:** Flutter Driver connect failed with HTTP 403
   - **Cause:** VM Service URL includes auth token path (e.g., `/1wQVtz5YTB0=/`), but we were connecting to `/ws`
   - **Solution:** Updated client to accept full URI and construct WebSocket URL as `ws://host:port/token/ws`

2. **websockets Package Not Found**
   - **Problem:** Server returned "websockets package required"
   - **Cause:** Update script installed to system Python, but server uses venv
   - **Solution:** Changed `pip3 install --user` to `$INSTALL_DIR/.venv/bin/pip install`

3. **VM Service Port Discovery**
   - **Problem:** VM Service uses random port each launch, need to find and forward it
   - **Solution:** Created `flutter_driver_discover` tool that:
     - Parses `adb logcat` for "Dart VM service is listening on"
     - Extracts port and auth token from URI
     - Runs `adb forward tcp:9223 tcp:<device_port>`
     - Returns ready-to-use URI

4. **Response Field Mismatch**
   - **Problem:** `flutter_get_text` and `flutter_widget_tree` returned null
   - **Cause:** Code looked for `response.get("text")` but Flutter Driver returns `{"response": "value"}`
   - **Solution:** Changed to `response.get("response") or response.get("text")`

5. **Test App Platform Support**
   - **Problem:** Host Mac couldn't run test app - "no supported devices"
   - **Cause:** Deployed only pubspec.yaml and main.dart, no android/ folder
   - **Solution:** Build APK in VM and deploy via ADB instead of syncing source

6. **flutter run from VM Fails**
   - **Problem:** `flutter run` from VM can't connect to VM Service
   - **Cause:** Port forwarding through ADB relay doesn't work for VM Service discovery
   - **Status:** Known issue - use `adb shell am start` + `flutter_driver_discover` instead
   - **Note:** This is the Phase 5 hot reload issue

## Deviations from Original Plan

### 1. Screenshot Implementation
**Plan:** Simple `takeScreenshot` command
**Actual:** Required multiple fixes:
- Maestro needed explicit `appId` (not empty string)
- Needed `launchApp` command before screenshot
- Needed absolute path for screenshot output
- Maestro adds `.png` automatically (caused double extension bug)

### 2. Assert Commands
**Plan:** Exact text matching
**Actual:** Changed to regex partial matching (`.*text.*`) for reliability

### 3. Swipe Command
**Plan:** Use `scroll` for vertical, `swipe` for horizontal
**Actual:** Use `swipe` for all directions - `scroll` syntax was incorrect

### 4. Default App ID
**Plan:** Empty appId, Maestro auto-detects
**Actual:** Explicit default `com.example.flutter_control_test_app` required

## Benchmark Results (Pre-Phase 2)

**Screenshot Performance (20 runs each):**

| Method | Avg Time | Min | Max | Notes |
|--------|----------|-----|-----|-------|
| ADB Direct | 220ms | 204ms | 472ms | Via relay from VM |
| Maestro | 15,524ms | 14,566ms | 17,700ms | Via MCP |

**Result: ADB is 70x faster than Maestro for screenshots**

**Recommendation:** Add ADB-based screenshot option for performance-critical workflows.

## Current File Structure

```
~/Projects/pl.erace.claude.flutter.control/
├── CLAUDE.md                 # Project instructions
├── TODO.md                   # Task tracking
├── PROJECT_STATUS.md         # This file
├── requirements.txt          # Python deps (fastapi, uvicorn, websockets)
├── flutter-control-stdio.py  # Stdio proxy for VM
├── flutter_control/          # Main package
│   ├── __init__.py
│   ├── config.py             # Ports, timeouts, app_id, observatory ports
│   ├── logging/
│   │   ├── __init__.py
│   │   └── trace.py          # Trace logging
│   ├── maestro/              # Phase 1: Maestro backend
│   │   ├── __init__.py
│   │   ├── flow_builder.py   # YAML generation
│   │   ├── parser.py         # Output parsing
│   │   └── wrapper.py        # CLI wrapper
│   ├── driver/               # Phase 2: Flutter Driver backend
│   │   ├── __init__.py
│   │   ├── client.py         # Observatory WebSocket client
│   │   ├── commands.py       # High-level driver commands
│   │   ├── finders.py        # Widget finders (ByKey, ByType, etc.)
│   │   └── protocol.py       # JSON-RPC protocol
│   ├── unified/              # Phase 3: Unified API
│   │   ├── __init__.py
│   │   ├── backend_selector.py  # Auto-select backend based on finder
│   │   └── executor.py       # Execute with fallback
│   └── mcp/
│       ├── __init__.py
│       ├── server.py         # FastAPI server
│       └── tools.py          # Tool definitions (Phase 1 + Phase 2)
├── scripts/
│   ├── install.sh            # Fresh install
│   └── update-host.sh        # Update deployment
├── test_app/                 # Flutter test app
│   ├── lib/main.dart         # App with driver extension enabled
│   └── pubspec.yaml          # Includes flutter_driver dep
└── tests/                    # Test directory (empty)
```

## Key Configuration

| Setting | Value | Location |
|---------|-------|----------|
| MCP Port | 9225 | config.py |
| Observatory Port (Android) | 9223 | config.py |
| Observatory Port (iOS) | 9224 | config.py |
| Default App ID | com.example.flutter_control_test_app | config.py |
| Default Timeout | 30s | config.py |
| Screenshot Dir | ~/Library/Logs/flutter-control/screenshots/ | config.py |
| Maestro Flow Dir | ~/Library/Logs/flutter-control/maestro/ | config.py |
| Auth Token | ~/.android-mcp-token | Shared with android-mcp-bridge |

## Known Issues

1. **Hot Reload Not Working**
   - VM Service connection fails from VM
   - Requires Observatory relay (Phase 5)

2. **Maestro Screenshot Slow**
   - 15+ seconds per screenshot
   - ADB is 70x faster
   - Consider adding ADB alternative

3. **No Integration Tests**
   - Plan called for automated tests
   - Currently manual testing only

## Next Steps (Phase 4: iOS Support)

1. Boot iOS Simulator
2. Install test app on iOS
3. Configure Observatory port 9224 for iOS
4. Run all tests against iOS
5. Verify cross-platform parity

## Working Workflow

From VM, fully automated:
```bash
# 1. Build and install app
cd test_app && flutter build apk --debug
adb install -r build/app/outputs/flutter-apk/app-debug.apk

# 2. Launch app
adb shell am start -n com.example.flutter_control_test_app/.MainActivity

# 3. Setup driver connection (for key/type finders)
flutter_driver_discover  # Returns URI + sets up port forwarding
flutter_driver_connect   # Pass the URI

# 4. Use unified API - backend auto-selected!
flutter_tap {text: "Submit"}     # → uses Maestro
flutter_tap {key: "submit_btn"}  # → uses Driver
flutter_assert_visible {text: "Success"}  # → uses Maestro

# 5. Or force specific backend
flutter_tap {text: "Submit", backend: "driver"}  # Force Driver
```

**Response includes backend info:**
```json
{
  "success": true,
  "backend": "maestro",
  "backends_tried": ["maestro"],
  "fallback": false
}
```

## To Resume This Project

```bash
# In VM
cd ~/Projects/pl.erace.claude.flutter.control

# Start HTTP server for deployment
python3 -m http.server 9999 --bind 0.0.0.0

# On host Mac - update deployment
curl -sS http://claude-dev.local:9999/scripts/update-host.sh | bash

# Verify
curl http://localhost:9225/health
```

## Architecture Learnings

### VM Service Connection
```
Flutter App (on emulator)
    └── VM Service listening on 127.0.0.1:<random_port>/<auth_token>/
            │
            │ adb forward tcp:9223 tcp:<random_port>
            ▼
Host Mac localhost:9223/<auth_token>/
            │
            │ MCP Server connects via WebSocket
            ▼
ws://localhost:9223/<auth_token>/ws
```

### Key Insight: Auth Token in URL
The VM Service URL includes an authentication token as a path segment:
- `http://127.0.0.1:42291/1wQVtz5YTB0=/`
- WebSocket must connect to: `ws://localhost:9223/1wQVtz5YTB0=/ws`
- Without the token path, connection returns HTTP 403

### Deployment Pattern
User only runs `curl ... | bash` on host. Everything else from VM:
1. Code changes in VM
2. HTTP server in VM serves files
3. User runs update script on host
4. VM builds APK, installs via ADB relay
5. VM controls app via MCP tools

### Unified API (Phase 3)
```
flutter_tap({text: "Submit"})
        │
        ▼
  BackendSelector.select()
        │
        ├── text/id finder? → Maestro primary
        └── key/type finder? → Driver primary
        │
        ▼
  UnifiedExecutor.tap()
        │
        ├── Try primary backend
        │   ├── Success → return
        │   └── Fail → try fallback
        │
        └── Try fallback backend (if available)
            ├── Success → return (fallback=true)
            └── Fail → return error
```

**Backend Selection Table:**
| Finder | Primary | Fallback | Reason |
|--------|---------|----------|--------|
| `{text: "..."}` | Maestro | Driver | Accessibility layer, but Driver can find by text too |
| `{id: "..."}` | Maestro | - | Android resource ID, Maestro only |
| `{key: "..."}` | Driver | - | Widget Key, requires widget tree |
| `{type: "..."}` | Driver | - | Widget type, requires widget tree |

## Related Projects

- **android-mcp-bridge**: Device/emulator management (port 9222)
- **ADB Relay**: ~/.android-mcp/adb-relay.py (localhost:5037 → host:15037)
- **Plan Document**: ~/Projects/android-mcp-bridge/PLAN-flutter-control.md
