#!/bin/bash
# Cleanup legacy Flutter Control installation
# Run this BEFORE installing the new pip-based version

set -e

echo "=== Flutter Control - Legacy Cleanup ==="
echo ""

# Stop and remove LaunchAgents
LAUNCH_AGENTS=(
    "$HOME/Library/LaunchAgents/com.flutter.control.plist"
    "$HOME/Library/LaunchAgents/com.erace.flutter-control.plist"
    "$HOME/Library/LaunchAgents/com.erace.flutter-control.ios.plist"
    "$HOME/Library/LaunchAgents/com.erace.flutter-control.android.plist"
    "$HOME/Library/LaunchAgents/com.erace.flutter-control.adb-relay.plist"
    "$HOME/Library/LaunchAgents/com.erace.flutter-control.observatory-relay.plist"
)

echo "Stopping services..."
for plist in "${LAUNCH_AGENTS[@]}"; do
    if [ -f "$plist" ]; then
        echo "  Unloading: $(basename $plist)"
        launchctl unload "$plist" 2>/dev/null || true
        rm -f "$plist"
    fi
done

# Remove installation directory
if [ -d "/usr/local/opt/flutter_control" ]; then
    echo "Removing /usr/local/opt/flutter_control..."
    sudo rm -rf /usr/local/opt/flutter_control
fi

# Note: Keep logs and token (shared with other tools)
echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Kept (shared resources):"
echo "  - ~/Library/Logs/flutter-control/ (logs)"
echo "  - ~/.android-mcp-token (auth token)"
echo ""
echo "Next: Install new version with pip:"
echo "  python3 -m venv ~/.flutter-control-venv"
echo "  source ~/.flutter-control-venv/bin/activate"
echo "  pip install git+https://github.com/erace/flutter-control-mcp.git"
echo "  flutter-control-install"
