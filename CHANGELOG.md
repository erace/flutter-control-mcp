# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.1] - 2026-02-04

### Added
- **`/upload-app` HTTP endpoint**: Unified app deployment
  - iOS: Upload .app bundle as zip, auto-extract and install via simctl
  - Android: Upload .apk directly, install via adb
  - Optional headers: `X-Bundle-Id`, `X-Device`, `X-Launch`
- **Headless mode**: `headless` parameter for simulator/emulator start
  - `ios_start_simulator {headless: true}` - run without window
  - Env var: `FLUTTER_CONTROL_HEADLESS=true` for default
- **Test suite for upload-app**: Comprehensive tests in `tests/test_upload_app.py`

### Changed
- **Consistent tool naming**: All lifecycle tools now use start/stop pattern
  - `ios_boot_simulator` → `ios_start_simulator`
  - `ios_shutdown_simulator` → `ios_stop_simulator`
  - `android_boot_emulator` → `android_start_emulator`
  - `android_shutdown_emulator` → `android_stop_emulator`
- **Screenshot output**: Now saves to file and returns path instead of base64
  - Path: `~/Library/Logs/flutter-control/screenshots/<timestamp>.png`
  - Reduces response size from ~150-230KB to ~100 bytes

### Fixed
- **Graceful MCP shutdown**: Added signal handlers (SIGTERM, SIGINT)
  - Eliminates "MCP failed" errors on Claude Code exit
- Datetime deprecation warnings (using timezone-aware datetimes)

## [0.5.0] - 2026-02-03

### Added
- **uvx/pipx support**: Standard MCP installation pattern
  - New `flutter-control-mcp` CLI entry point for stdio MCP server
  - Works with `uvx flutter-control-mcp` (no install needed)
- Version-agnostic `update.sh` script (auto-detects wheel version)

### Changed
- **Simplified configuration**: Single `ANDROID_HOST` env var for all Android services
  - Replaces: `ANDROID_MCP_HOST`, `ANDROID_MCP_PORT`, `ANDROID_MCP_BRIDGE_HOST`, `ANDROID_MCP_BRIDGE_PORT`
  - Defaults to `phost.local` (mDNS) - works across networks
  - Ports use sensible defaults (9225 for Flutter Control, 9222 for Bridge)
- MCP client config now uses uvx pattern
- Test bootstrap properly passes `ADB_SERVER_SOCKET` to subprocesses
- Fixed device ID parsing for Android MCP Bridge output format

### Removed
- Legacy curl-based installation scripts (`scripts/install.sh`, `scripts/update-host.sh`)
- Standalone `flutter-control-stdio.py` (moved to `flutter_control.cli:mcp_stdio`)
- Deprecated env vars: `ANDROID_MCP_HOST`, `ANDROID_MCP_BRIDGE_HOST` (use `ANDROID_HOST`)

### Fixed
- Bootstrap now creates venv if missing during updates
- ADB commands in test bootstrap now work with remote ADB server

## [0.4.0] - 2026-02-03

### Added
- `android_list_devices`: List Android emulators, devices, and AVDs
- `android_boot_emulator`: Start emulator by AVD name
- `android_shutdown_emulator`: Stop Android emulator
- iOS simctl screenshot support (fast native method)

### Changed
- `flutter_screenshot` now auto-selects fastest method per platform:
  - Android: ADB screencap
  - iOS: simctl io screenshot
  - Falls back to Maestro on error
- Renamed `flutter_screenshot` (Maestro) to `flutter_screenshot_maestro`
- Removed `flutter_screenshot_adb` (merged into smart `flutter_screenshot`)
- Consolidated `flutter_debug_traces` into `flutter_debug_trace`:
  - `flutter_debug_trace {trace_id: "..."}` - get specific trace
  - `flutter_debug_trace {count: N}` - get recent traces
  - `flutter_debug_trace {}` - get last 5 traces

### Removed
- `flutter_screenshot_adb` - use `flutter_screenshot` instead
- `flutter_debug_traces` - use `flutter_debug_trace` instead

## [0.3.0] - 2026-02-03

### Added
- mDNS discovery as primary method for both iOS and Android
- `update.sh` script for easy host deployment via pip wheel
- Version endpoint now reads from `__version__.py`

### Changed
- Discovery falls back to logcat for Android when mDNS unavailable
- Port scan fallback for iOS as last resort
- Android environment warnings only shown for Android tests
- Simplified bootstrap to use MCP tools consistently

### Fixed
- Hardcoded version in server.py now imports from `__version__.py`

## [0.2.0] - 2025-02-03

### Added
- pip installation from GitHub (`pip install git+https://...`)
- CLI commands: `flutter-control-install`, `flutter-control-uninstall`, `flutter-control-server`
- README.md with installation and usage instructions

## [0.1.0] - 2025-02-03

### Added
- Initial release of Flutter Control MCP server
- **Maestro backend**: UI automation via accessibility layer
  - Tap, double tap, long press gestures
  - Text input and clearing
  - Swipe gestures (up/down/left/right)
  - Assert visible/not visible
  - Screenshots
  - View hierarchy inspection
- **Flutter Driver backend**: Widget-tree automation
  - Connect/disconnect to Flutter VM Service
  - Auto-discovery of VM Service URI with port forwarding
  - Tap by key, type, or text
  - Get text from widgets
  - Widget tree inspection
- **Unified API**: Auto-selects backend based on finder type
  - `{text: "..."}` or `{id: "..."}` → Maestro
  - `{key: "..."}` or `{type: "..."}` → Flutter Driver
  - Automatic fallback on failure
- **Maestro MCP persistent connection**: 9-25x faster operations
  - Persistent `maestro mcp` subprocess with JSON-RPC
  - Large response handling (screenshots 130KB+)
  - Auto-reconnect on process death
- **Cross-platform support**
  - Android emulator (via host Mac)
  - iOS simulator (via VM)
  - mDNS hostname resolution (network-agnostic)
- **Test infrastructure**
  - Automatic device/emulator bootstrap
  - Environment validation warnings
  - Comprehensive test suite (48 tests)

### Performance
- Tap operations: ~1.5s (was ~14s with legacy Maestro)
- Screenshots: ~0.6s (was ~15s)
- View hierarchy: ~0.5s (was ~15s)

[Unreleased]: https://github.com/erace/flutter-control-mcp/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/erace/flutter-control-mcp/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/erace/flutter-control-mcp/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/erace/flutter-control-mcp/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/erace/flutter-control-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/erace/flutter-control-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/erace/flutter-control-mcp/releases/tag/v0.1.0
