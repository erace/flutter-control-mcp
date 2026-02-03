# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/erace/flutter-control-mcp/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/erace/flutter-control-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/erace/flutter-control-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/erace/flutter-control-mcp/releases/tag/v0.1.0
