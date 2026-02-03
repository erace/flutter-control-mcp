# Flutter Control - TODOs

## Phase 1 - COMPLETED ✅

All Maestro-based tools working:
- `flutter_tap` ✅
- `flutter_double_tap` ✅
- `flutter_long_press` ✅
- `flutter_swipe` ✅ (fixed: use `swipe` command, not `scroll`)
- `flutter_enter_text` ✅ (supports `id` finder for TextFields)
- `flutter_clear_text` ✅
- `flutter_assert_visible` ✅ (fixed: uses regex `.*text.*` for partial matching)
- `flutter_assert_not_visible` ✅
- `flutter_screenshot` ✅ (fixed: uses absolute path, returns base64)
- `flutter_debug_traces` ✅
- `flutter_debug_trace` ✅

### Fixes Applied
1. **assert_visible/assert_not_visible**: Now uses regex partial matching (`.*text.*`) by default
2. **enter_text**: Supports both `text` and `id` finders; `id` preferred for TextFields
3. **swipe**: Changed from `scroll` to `swipe` command with direction
4. **screenshot**: Uses absolute path in `~/Library/Logs/flutter-control/screenshots/`, returns base64 PNG
5. **All tools**: Added `app_id` parameter with default `com.example.flutter_control_test_app`

## Pending Tasks

### Benchmark (Pre-Phase 2) - COMPLETED ✅

**Screenshot Performance (20 runs each):**

| Method | Avg Time | Min | Max |
|--------|----------|-----|-----|
| ADB Direct (via relay) | 220ms | 204ms | 472ms |
| Maestro (via MCP) | 15,524ms | 14,566ms | 17,700ms |

**Result: ADB is 70x faster than Maestro for screenshots.**

**Recommendation:** Use ADB for screenshots via:
```bash
/Users/admin/Library/Android/sdk/platform-tools/adb exec-out screencap -p > screenshot.png
```
Keep Maestro for semantic UI interactions (tap, assert, etc.) where it provides value.

### Phase 2 - Flutter Driver Backend - COMPLETE ✅

**Implemented & Tested:**
- [x] Observatory WebSocket client (`flutter_control/driver/client.py`)
- [x] Flutter Driver protocol (`flutter_control/driver/protocol.py`)
- [x] Widget finders: ByKey, ByType, ByText, ByTooltip, BySemanticsLabel
- [x] `flutter_driver_discover` - auto-discovers VM service URI + port forwarding
- [x] `flutter_driver_connect` / `flutter_driver_disconnect` - tested ✅
- [x] `flutter_get_text` - tested: returns correct text ✅
- [x] `flutter_widget_tree` - tested: returns 614KB tree ✅
- [x] `flutter_driver_tap` - tested: counter 1→2 ✅
- [x] `flutter_run` tool
- [x] Test app with `enableFlutterDriverExtension()`

**Key Discovery:** VM service URL includes auth token path (e.g., `/abc123=/`). The `flutter_driver_discover` tool extracts this automatically.

### Phase 3 - Unified API + Auto-Fallback - COMPLETE ✅

**Implemented & Tested:**
- [x] Backend selector (`flutter_control/unified/backend_selector.py`)
- [x] Unified executor with fallback (`flutter_control/unified/executor.py`)
- [x] `flutter_tap` now auto-selects: text/id → Maestro, key/type → Driver
- [x] `flutter_assert_visible` now auto-selects backend
- [x] Force backend with `backend: "maestro"` or `"driver"`
- [x] Response includes `backend`, `backends_tried`, `fallback` fields

**Backend Selection Rules:**
| Finder | Primary Backend | Fallback |
|--------|----------------|----------|
| `{text: "..."}` | Maestro | Driver |
| `{id: "..."}` | Maestro | none |
| `{key: "..."}` | Driver | none |
| `{type: "..."}` | Driver | none |

### Phase 5 - Hot Reload
- [ ] Fix Flutter hot reload from VM (VM Service connection fails)
- [ ] Create Observatory relay to forward ports 9223/9224
- [ ] See PLAN-flutter-control.md for details

## Future Enhancements

### High Priority
- [ ] Add `waitForVisible` tool with configurable polling
- [ ] Add `scrollUntilVisible` for finding items in lists
- [x] Support `key` finder for Flutter widget keys (Phase 2) - DONE
- [x] Add `flutter_get_text` to read text from elements - DONE

### Medium Priority
- [ ] iOS support (Maestro works on iOS too) - Phase 4
- [ ] Better error messages from Maestro output parsing
- [ ] Maestro studio mode for faster execution

### Low Priority
- [ ] Parallel test execution
- [ ] Record/playback mode
- [ ] Screenshot comparison/diff

## Architecture Notes

### Phase 1 Flow (Maestro):
```
VM (Claude) → HTTP → Host MCP Server → Maestro CLI → Device
```

### Phase 2 Flow (Flutter Driver):
```
VM (Claude) → HTTP → Host MCP Server → WebSocket → Observatory → Device
                                              ↑
                                     adb forward tcp:9223 tcp:<port>
```

### Key Discovery: VM Service Auth Token
The VM Service URL includes an auth token path that MUST be included in WebSocket URL:
```
VM Service: http://127.0.0.1:42291/1wQVtz5YTB0=/
WebSocket:  ws://localhost:9223/1wQVtz5YTB0=/ws  ← token required!
```

### Deployment Pattern
- User ONLY runs `curl ... | bash` on host
- Claude does everything else from VM:
  - Code changes
  - Build APK
  - Install via ADB
  - Control via MCP tools

### Potential Optimizations:
- Keep Maestro in "studio" mode for faster command execution
- Use ADB for simple operations (screenshot, tap coordinates)
- Cache VM service connection across commands

## Backlog

### MCP shutdown message on Claude Code exit
- **Issue**: Claude Code shows "3 MCP failed" message when exiting
- **Status**: Cosmetic only - servers exit cleanly with code 0
- **Cause**: Claude Code reports all disconnected MCP servers as "failed" regardless of clean shutdown
- **Possible fixes**:
  - Investigate if MCP protocol has a specific shutdown handshake
  - Check if Claude Code expects a specific response before disconnect
  - May require upstream fix in Claude Code
