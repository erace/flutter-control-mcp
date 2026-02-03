# Flutter Control MCP - Integration Tests

Comprehensive integration test suite for Flutter Control MCP tools.

## Quick Start (from VM)

```bash
# 1. Activate venv
cd /Users/admin/Projects/pl.erace.claude.flutter.control
source .venv/bin/activate

# 2. Deploy test app to Android (if needed)
export PATH="$PATH:/Users/admin/Library/Android/sdk/platform-tools"
cd test_app && flutter build apk --debug
adb install -r build/app/outputs/flutter-apk/app-debug.apk
adb shell am start -n com.example.flutter_control_test_app/.MainActivity
cd ..

# 3. Run tests
# Android (from VM - note the host IP!)
TEST_PLATFORM=android ANDROID_MCP_HOST=phost.local ANDROID_MCP_PORT=9225 pytest tests/ -v -m "not driver_only"

# iOS
TEST_PLATFORM=ios IOS_MCP_PORT=9226 pytest tests/ -v -m "not driver_only"
```

## Setup

```bash
# Install test dependencies (already in .venv)
source .venv/bin/activate
pip install pytest pytest-asyncio httpx
```

## Prerequisites

Before running tests:

1. **Android**: Start emulator with test app running
   ```bash
   # From VM - deploy test app
   export PATH="$PATH:/Users/admin/Library/Android/sdk/platform-tools"
   cd test_app && flutter build apk --debug
   adb install -r build/app/outputs/flutter-apk/app-debug.apk
   adb shell am start -n com.example.flutter_control_test_app/.MainActivity
   ```

2. **iOS**: Start simulator with test app running
   ```bash
   # iOS simulator should already have app from flutter run
   # Or deploy via Xcode
   ```

3. **MCP Servers**: Ensure servers are running
   ```bash
   # Check Android server (host Mac at phost.local)
   curl http://phost.local:9225/health

   # Check iOS server (VM localhost)
   curl http://localhost:9226/health
   ```

4. **Driver Connection** (for driver_only tests):
   ```bash
   # Discover and connect to VM Service
   # Run flutter_driver_discover first, then flutter_driver_connect with the URI
   ```

## Running Tests

### Basic Usage (FROM VM)

**IMPORTANT**: When running from VM, you must set correct MCP host for Android!

```bash
# Android - MUST set ANDROID_MCP_HOST to host Mac IP
TEST_PLATFORM=android ANDROID_MCP_HOST=phost.local ANDROID_MCP_PORT=9225 pytest tests/ -v -m "not driver_only"

# iOS - localhost works
TEST_PLATFORM=ios IOS_MCP_PORT=9226 pytest tests/ -v -m "not driver_only"

# Skip driver tests (recommended unless driver is connected)
pytest tests/ -v -m "not driver_only"
```

### Filtering Tests

```bash
# Skip slow tests
pytest tests/ -v -m "not slow"

# Only tap tests
pytest tests/test_tap.py -v

# Only driver tests
pytest tests/ -v -m "driver_only"

# Only Maestro tests
pytest tests/ -v -m "maestro_only"

# Skip driver tests (if not connected)
pytest tests/ -v -m "not driver_only"
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_PLATFORM` | `android` | Platform to test (`android` or `ios`) |
| `ANDROID_MCP_HOST` | `phost.local` | Android MCP server host (**host Mac IP from VM**) |
| `ANDROID_MCP_PORT` | `9225` | Android MCP server port |
| `IOS_MCP_HOST` | `localhost` | iOS MCP server host |
| `IOS_MCP_PORT` | `9226` | iOS MCP server port |
| `ANDROID_VM_SERVICE_URI` | - | VM Service URI for Android driver |
| `IOS_VM_SERVICE_URI` | - | VM Service URI for iOS driver |
| `TEST_DEVICE_ID` | - | Specific device ID to test on |
| `FLUTTER_CONTROL_TOKEN` | - | Auth token (or reads from ~/.android-mcp-token) |

**Note**: If shell has stale env vars, explicitly set them: `ANDROID_MCP_HOST=phost.local`

## Test Categories

### 3-Backend Tests

These tests measure timing for all 3 backends (unified, maestro, driver):

- `test_tap.py` - Tap operations
- `test_assertions.py` - Assert visible/not visible

### Maestro-Only Tests

Tests that only work with Maestro:

- `test_gestures.py` - Swipe, double tap, long press
- `test_text_input.py` - Enter text, clear text

### Driver-Only Tests

Tests that require Flutter Driver connection:

- `test_driver_only.py` - get_text, widget_tree, connect/disconnect

### Screenshot Tests

- `test_screenshots.py` - Maestro vs ADB screenshot comparison

## Test Report

After running tests, a timing report is generated at:

```
tests/reports/timing_report.md
```

The report shows:
- 3-backend comparison (unified, maestro, driver)
- Maestro-only operation timings
- Driver-only operation timings
- Screenshot method comparison
- Summary of successes/failures

## Adding New Tests

1. Create a new test file `tests/test_<category>.py`
2. Use the provided fixtures:
   - `mcp_client` - Async HTTP client for MCP calls
   - `platform` - Current platform name
   - `timing_collector` - Records timing for report
3. Use timing context manager:
   ```python
   async with timing_collector.measure("operation_name", platform, backend="unified"):
       result = await mcp_client.call("flutter_tap", {"finder": {"text": "Button"}})
   ```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check MCP server is running |
| Auth error | Ensure token file exists at `~/.android-mcp-token` |
| Driver tests fail | Run `flutter_driver_discover` and `flutter_driver_connect` first |
| Slow tests timeout | Use `pytest --timeout=120` or skip with `-m "not slow"` |
| Android tests fail with wrong host | Set `ANDROID_MCP_HOST=phost.local` explicitly |
| Maestro timeout (30s) | Restart host service: `launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control.android` |
| "No space left on device" | Run `rm -rf ~/.gradle/caches` then rebuild |
| ADB not found | `export PATH="$PATH:/Users/admin/Library/Android/sdk/platform-tools"` |

## ADB Path (VM)

```bash
export PATH="$PATH:/Users/admin/Library/Android/sdk/platform-tools"
```

## Test Results (Latest Run)

| Platform | Passed | Failed | Skipped | Duration |
|----------|--------|--------|---------|----------|
| Android | 48 | 0 | 1 | ~6 min |

Skipped: `test_get_text_by_type` - finding by generic `{type: "Text"}` matches multiple widgets
