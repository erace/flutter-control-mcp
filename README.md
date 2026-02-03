# Flutter Control MCP

MCP server for Flutter UI automation via Maestro and Flutter Driver.

## Features

- **Maestro backend**: Accessibility-layer automation (works on any app)
- **Flutter Driver backend**: Widget-tree automation (requires driver extension)
- **Unified API**: Auto-selects backend based on finder type
- **Fast operations**: Persistent Maestro MCP connection (9-25x faster)
- **Cross-platform**: Android emulator + iOS simulator

## Installation

### From GitHub

```bash
# Create a virtual environment (recommended)
python3 -m venv ~/.flutter-control-venv
source ~/.flutter-control-venv/bin/activate

# Install from GitHub
pip install git+https://github.com/erace/flutter-control-mcp.git

# Install as macOS service
flutter-control-install
```

### From specific version

```bash
pip install git+https://github.com/erace/flutter-control-mcp.git@v0.1.0
```

### Upgrade

```bash
pip install --upgrade git+https://github.com/erace/flutter-control-mcp.git
flutter-control-install  # Restart service with new version
```

## Usage

### Service Management

```bash
# Install service (default port 9225)
flutter-control-install

# Install on custom port
flutter-control-install --port 9226

# Uninstall service
flutter-control-install --uninstall

# Check version
flutter-control --version
```

### API Endpoints

```bash
# Health check
curl http://localhost:9225/health

# List available tools
curl http://localhost:9225/tools

# Call a tool
curl -X POST http://localhost:9225/call \
  -H "Authorization: Bearer $(cat ~/.android-mcp-token)" \
  -H "Content-Type: application/json" \
  -d '{"name": "flutter_tap", "arguments": {"finder": {"text": "Submit"}}}'
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `flutter_tap` | Tap on element by text, key, type, or id |
| `flutter_double_tap` | Double tap on element |
| `flutter_long_press` | Long press on element |
| `flutter_swipe` | Swipe in direction |
| `flutter_enter_text` | Enter text into field |
| `flutter_clear_text` | Clear text field |
| `flutter_assert_visible` | Assert element is visible |
| `flutter_assert_not_visible` | Assert element is not visible |
| `flutter_screenshot` | Take screenshot (Maestro) |
| `flutter_screenshot_adb` | Take screenshot (ADB, faster) |
| `flutter_get_text` | Get text from widget |
| `flutter_widget_tree` | Get widget tree |
| `flutter_driver_connect` | Connect to Flutter Driver |
| `flutter_driver_disconnect` | Disconnect from Flutter Driver |
| `flutter_version` | Get version info |

### Finder Types

| Finder | Backend | Example |
|--------|---------|---------|
| `{text: "..."}` | Maestro | `{"text": "Submit"}` |
| `{id: "..."}` | Maestro | `{"id": "btn_submit"}` |
| `{key: "..."}` | Driver | `{"key": "submit_button"}` |
| `{type: "..."}` | Driver | `{"type": "ElevatedButton"}` |

## Requirements

- Python 3.11+
- macOS (for LaunchAgent service)
- [Maestro](https://maestro.mobile.dev/) for UI automation
- Android SDK (for Android automation)
- Xcode (for iOS automation)

### Install Maestro

```bash
curl -Ls "https://get.maestro.mobile.dev" | bash
```

## Flutter App Setup

To use Flutter Driver backend, add to your app's `main.dart`:

```dart
import 'package:flutter_driver/driver_extension.dart';

void main() {
  assert(() {
    enableFlutterDriverExtension();
    return true;
  }());
  runApp(const MyApp());
}
```

And `pubspec.yaml`:

```yaml
dev_dependencies:
  flutter_driver:
    sdk: flutter
```

## Development

```bash
# Clone
git clone https://github.com/erace/flutter-control-mcp.git
cd flutter-control-mcp

# Install dev dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run server directly
flutter-control-server
```

## License

MIT
