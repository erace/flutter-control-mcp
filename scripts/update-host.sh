#!/bin/bash
# Update Flutter Control MCP server on host Mac
# Run: curl -sS http://claude-dev.local:9999/scripts/update-host.sh | bash

set -e

INSTALL_DIR="/usr/local/opt/flutter_control"
VM_IP="${VM_IP:-claude-dev.local}"
VM_PORT="${VM_PORT:-9999}"
LOG_DIR="$HOME/Library/Logs/flutter-control"

echo "=== Updating Flutter Control (Phase 6) ==="

# Clean up old directory structure (from previous installations)
echo "Cleaning up old files..."
rm -rf "$INSTALL_DIR/logging" "$INSTALL_DIR/maestro" "$INSTALL_DIR/mcp" \
       "$INSTALL_DIR/driver" "$INSTALL_DIR/unified" \
       "$INSTALL_DIR/__init__.py" "$INSTALL_DIR/config.py"

# Create directories (flutter_control is the package inside INSTALL_DIR)
PKG_DIR="$INSTALL_DIR/flutter_control"
mkdir -p "$PKG_DIR"/{logging,maestro,mcp,driver,unified}
mkdir -p "$INSTALL_DIR"/{scripts,bin}
mkdir -p "$INSTALL_DIR/test_app/lib"
mkdir -p "$LOG_DIR"

# Download core files
echo "Downloading core files..."
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/__init__.py" -o "$PKG_DIR/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/config.py" -o "$PKG_DIR/config.py"

# Logging module
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/logging/__init__.py" -o "$PKG_DIR/logging/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/logging/trace.py" -o "$PKG_DIR/logging/trace.py"

# Maestro module
echo "Downloading Maestro module..."
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/maestro/__init__.py" -o "$PKG_DIR/maestro/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/maestro/flow_builder.py" -o "$PKG_DIR/maestro/flow_builder.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/maestro/parser.py" -o "$PKG_DIR/maestro/parser.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/maestro/wrapper.py" -o "$PKG_DIR/maestro/wrapper.py"

# Driver module
echo "Downloading Driver module..."
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/__init__.py" -o "$PKG_DIR/driver/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/client.py" -o "$PKG_DIR/driver/client.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/commands.py" -o "$PKG_DIR/driver/commands.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/finders.py" -o "$PKG_DIR/driver/finders.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/protocol.py" -o "$PKG_DIR/driver/protocol.py"

# MCP module
echo "Downloading MCP module..."
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/mcp/__init__.py" -o "$PKG_DIR/mcp/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/mcp/tools.py" -o "$PKG_DIR/mcp/tools.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/mcp/server.py" -o "$PKG_DIR/mcp/server.py"

# Unified module
echo "Downloading Unified module..."
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/unified/__init__.py" -o "$PKG_DIR/unified/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/unified/backend_selector.py" -o "$PKG_DIR/unified/backend_selector.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/unified/executor.py" -o "$PKG_DIR/unified/executor.py"

# Scripts
echo "Downloading scripts..."
curl -sS "http://$VM_IP:$VM_PORT/scripts/observatory-bridge.py" -o "$INSTALL_DIR/scripts/observatory-bridge.py"
chmod +x "$INSTALL_DIR/scripts/observatory-bridge.py"

# Test app
echo "Downloading test app..."
curl -sS "http://$VM_IP:$VM_PORT/test_app/pubspec.yaml" -o "$INSTALL_DIR/test_app/pubspec.yaml"
curl -sS "http://$VM_IP:$VM_PORT/test_app/lib/main.dart" -o "$INSTALL_DIR/test_app/lib/main.dart"

# Install Python dependencies
echo "Installing Python dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install --quiet websockets 2>/dev/null || echo "Warning: Could not install websockets"

# === Phase 6: Cleanup old services ===
echo "Cleaning up old services..."

# Unload old services (ignore errors)
launchctl unload "$HOME/Library/LaunchAgents/com.flutter.control.plist" 2>/dev/null || true
launchctl unload "$HOME/Library/LaunchAgents/com.flutter.observatory-bridge.plist" 2>/dev/null || true

# Remove old plists
rm -f "$HOME/Library/LaunchAgents/com.flutter.control.plist"
rm -f "$HOME/Library/LaunchAgents/com.flutter.observatory-bridge.plist"

# === Create wrapper scripts (nice process names) ===
echo "Creating wrapper scripts..."

cat > "$INSTALL_DIR/bin/flutter-control-android" << 'WRAPPER'
#!/bin/bash
# Flutter Control MCP Server (Android)
exec /usr/local/opt/flutter_control/.venv/bin/python3 -c "
import sys
sys.path.insert(0, '/usr/local/opt/flutter_control')
from flutter_control.mcp.server import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=9225)
"
WRAPPER
chmod +x "$INSTALL_DIR/bin/flutter-control-android"

cat > "$INSTALL_DIR/bin/observatory-bridge" << 'WRAPPER'
#!/bin/bash
# Observatory Bridge - Exposes ADB forward to network
exec /usr/bin/python3 /usr/local/opt/flutter_control/scripts/observatory-bridge.py
WRAPPER
chmod +x "$INSTALL_DIR/bin/observatory-bridge"

# === Create new LaunchAgents with clean naming ===
echo "Creating LaunchAgents..."

# Android MCP Server
cat > "$HOME/Library/LaunchAgents/com.erace.flutter-control.android.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.erace.flutter-control.android</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/bin/flutter-control-android</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:$HOME/.maestro/bin</string>
        <key>FLUTTER_CONTROL_PORT</key>
        <string>9225</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/android-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/android-stderr.log</string>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
EOF

# Observatory Bridge
cat > "$HOME/Library/LaunchAgents/com.erace.flutter-control.observatory-bridge.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.erace.flutter-control.observatory-bridge</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/bin/observatory-bridge</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/observatory-bridge.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/observatory-bridge.log</string>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
EOF

# Load/restart services
echo "Starting services..."
# Unload first (ignore errors if not loaded)
launchctl bootout gui/$(id -u)/com.erace.flutter-control.android 2>/dev/null || true
launchctl bootout gui/$(id -u)/com.erace.flutter-control.observatory-bridge 2>/dev/null || true
sleep 1
# Load fresh
launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.erace.flutter-control.android.plist" 2>/dev/null || \
    launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control.android 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.erace.flutter-control.observatory-bridge.plist" 2>/dev/null || true

sleep 3

# Verify
echo ""
if curl -s http://localhost:9225/health | grep -q "ok"; then
    VERSION=$(curl -s http://localhost:9225/version 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    DEPLOYED=$(curl -s http://localhost:9225/version 2>/dev/null | grep -o '"deployed_at":"[^"]*"' | cut -d'"' -f4)
    echo "=== Update Complete ==="
    echo "Version: ${VERSION:-unknown}"
    echo "Deployed: ${DEPLOYED:-unknown}"
    echo ""
    echo "Services:"
    echo "  - com.erace.flutter-control.android (port 9225)"
    echo "  - com.erace.flutter-control.observatory-bridge (port 9233)"
    echo ""
    echo "Logs: $LOG_DIR/"
else
    echo "=== Warning: Service may need manual restart ==="
    echo "Check: tail -f $LOG_DIR/android-stderr.log"
fi
