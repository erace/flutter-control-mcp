# Refactor Plan: Tool Consolidation v0.4.0

## Overview

Consolidate and unify MCP tools for better consistency and usability.

## Rollback Point

```bash
git checkout 642b60d  # Last known good: v0.3.0 with README
```

## Changes Summary

| Change | Old | New |
|--------|-----|-----|
| Screenshot | `flutter_screenshot` + `flutter_screenshot_adb` | `flutter_screenshot` (smart) + `flutter_screenshot_maestro` |
| Android lifecycle | In android-mcp-bridge | Add to flutter-control |
| Debug traces | 2 tools | Merge into 1 |

## Implementation Phases

### Phase 1: Screenshot Consolidation
**Commit: "refactor: unify screenshot tools"**

1. Rename `flutter_screenshot` → `flutter_screenshot_maestro`
2. Rename `flutter_screenshot_adb` → internal `_adb_screenshot`
3. Add `_simctl_screenshot` for iOS
4. Create new `flutter_screenshot` that auto-selects:
   - iOS → simctl
   - Android → ADB
   - Fallback → Maestro

**Files:**
- `flutter_control/mcp/tools.py` - Tool definitions and handlers

**Tests:**
- Update `tests/test_screenshots.py` - Rename test references

### Phase 2: Android Lifecycle Tools
**Commit: "feat: add Android lifecycle tools"**

Add tools (mirror iOS naming):
- `android_list_devices` - List emulators and AVDs
- `android_boot_emulator` - Start emulator by AVD name
- `android_shutdown_emulator` - Stop emulator

**Files:**
- `flutter_control/mcp/tools.py` - Add tool definitions and handlers

**Tests:**
- Create `tests/test_android_lifecycle.py`

### Phase 3: Debug Tool Cleanup
**Commit: "refactor: consolidate debug tools"**

1. Merge `flutter_debug_traces` into `flutter_debug_trace`
   - `flutter_debug_trace` with no args → returns recent traces
   - `flutter_debug_trace {trace_id: "xxx"}` → returns specific trace
   - `flutter_debug_trace {count: 10}` → returns last 10 traces

**Files:**
- `flutter_control/mcp/tools.py`

**Tests:**
- Update any tests using debug tools

### Phase 4: Documentation & Version Bump
**Commit: "docs: update for v0.4.0"**

- Update `README.md` with new tool list
- Update `CHANGELOG.md`
- Bump version to `0.4.0`

**Files:**
- `README.md`
- `CHANGELOG.md`
- `flutter_control/__version__.py`
- `pyproject.toml`
- `update.sh`

### Phase 5: Test Suite Verification
**Commit: "test: verify all platforms"**

Run full test suite on both platforms:
```bash
# iOS
TEST_PLATFORM=ios IOS_MCP_PORT=9226 pytest tests/ -v

# Android
TEST_PLATFORM=android ANDROID_MCP_HOST=phost.local ANDROID_MCP_PORT=9225 pytest tests/ -v
```

## Final Tool List (25 tools)

### UI Interactions (6)
| Tool | Description |
|------|-------------|
| `flutter_tap` | Tap element |
| `flutter_double_tap` | Double tap |
| `flutter_long_press` | Long press |
| `flutter_swipe` | Swipe direction |
| `flutter_enter_text` | Type text |
| `flutter_clear_text` | Clear field |

### Assertions (2)
| Tool | Description |
|------|-------------|
| `flutter_assert_visible` | Check visible |
| `flutter_assert_not_visible` | Check not visible |

### Screenshots (2)
| Tool | Description |
|------|-------------|
| `flutter_screenshot` | Smart: ADB (Android) / simctl (iOS) |
| `flutter_screenshot_maestro` | Explicit Maestro |

### Flutter Driver (7)
| Tool | Description |
|------|-------------|
| `flutter_driver_discover` | Find VM Service |
| `flutter_driver_connect` | Connect |
| `flutter_driver_disconnect` | Disconnect |
| `flutter_driver_tap` | Tap via Driver |
| `flutter_get_text` | Get widget text |
| `flutter_widget_tree` | Dump tree |
| `flutter_run` | Launch with Observatory |

### iOS Lifecycle (3)
| Tool | Description |
|------|-------------|
| `ios_list_devices` | List simulators |
| `ios_boot_simulator` | Boot simulator |
| `ios_shutdown_simulator` | Shutdown simulator |

### Android Lifecycle (3)
| Tool | Description |
|------|-------------|
| `android_list_devices` | List emulators/AVDs |
| `android_boot_emulator` | Boot emulator |
| `android_shutdown_emulator` | Shutdown emulator |

### Debug (2)
| Tool | Description |
|------|-------------|
| `flutter_version` | Server info |
| `flutter_debug_trace` | Get trace(s) |

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Screenshot changes break tests | Keep `flutter_screenshot_maestro` as fallback |
| Android lifecycle doesn't work from host | Test on host before removing android-mcp-bridge |
| Rollback needed | Each phase is a separate commit |

## Verification Checklist

- [ ] Phase 1: Screenshot tests pass on both platforms
- [ ] Phase 2: Android lifecycle works from VM calling host
- [ ] Phase 3: Debug tool works with all parameter combinations
- [ ] Phase 4: README reflects actual tools
- [ ] Phase 5: Full test suite passes (iOS: 42+, Android: 47+)

## Post-Refactor

1. Update host Mac: `curl -sS http://claude-dev.local:9999/update.sh | bash`
2. Verify version: `curl http://phost.local:9225/version`
3. Consider deprecating android-mcp-bridge (keep for ADB proxy only)
