#!/bin/bash
# Install Flutter Control for iOS on Host Mac
# Run with: curl -sS http://claude-dev.local:9999/scripts/install-ios-host.sh | bash

set -e

VM_HOST="${VM_HOST:-claude-dev.local}"
WHEEL_URL="http://${VM_HOST}:9999/dist"
VENV_PATH="${HOME}/.flutter-control-venv"
LOG_DIR="${HOME}/Library/Logs/flutter-control"
PLIST_PATH="${HOME}/Library/LaunchAgents/com.erace.flutter-control.ios.plist"
PORT=9227

echo "=== Flutter Control iOS (Host Mac) Installation ==="

# Find the wheel
WHEEL_NAME=$(curl -sS "${WHEEL_URL}/" | grep -o 'flutter_control_mcp-[0-9.]*-py3-none-any.whl' | head -1)
if [ -z "$WHEEL_NAME" ]; then
    echo "Error: Could not find wheel at ${WHEEL_URL}/"
    exit 1
fi
echo "Found: $WHEEL_NAME"

# Create venv if missing
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating venv at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
fi

# Activate and install
source "$VENV_PATH/bin/activate"
pip install --upgrade pip -q
echo "Installing ${WHEEL_NAME}..."
pip install --force-reinstall "${WHEEL_URL}/${WHEEL_NAME}" -q

# Get installed version
VERSION=$(python3 -c "from flutter_control import __version__; print(__version__)")
echo "Installed version: $VERSION"

# Create log directory
mkdir -p "$LOG_DIR"

# Ensure token exists (shared with Android)
TOKEN_FILE="${HOME}/.android-mcp-token"
if [ ! -f "$TOKEN_FILE" ]; then
    echo "Generating auth token..."
    openssl rand -hex 16 > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
fi

# Find paths for Maestro and Flutter
MAESTRO_PATH="${HOME}/.maestro/bin"
FLUTTER_PATH=$(dirname "$(which flutter 2>/dev/null || echo "${HOME}/flutter/bin/flutter")")

# Build PATH
SERVICE_PATH="/usr/local/bin:/usr/bin:/bin:${MAESTRO_PATH}:${FLUTTER_PATH}"

# Create LaunchAgent plist
cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.erace.flutter-control.ios</string>
    <key>ProgramArguments</key>
    <array>
        <string>${VENV_PATH}/bin/python3</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>flutter_control.mcp.server:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>${PORT}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>FLUTTER_CONTROL_PORT</key>
        <string>${PORT}</string>
        <key>FLUTTER_CONTROL_HOST</key>
        <string>0.0.0.0</string>
        <key>PATH</key>
        <string>${SERVICE_PATH}</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/ios-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/ios-stderr.log</string>
</dict>
</plist>
PLIST

echo "Created LaunchAgent: $PLIST_PATH"

# Load the service
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

# Verify
sleep 2
if curl -s "http://localhost:${PORT}/health" >/dev/null 2>&1; then
    echo ""
    echo "=== Installation Complete ==="
    curl -s "http://localhost:${PORT}/version" | python3 -c "import sys,json; v=json.load(sys.stdin); print(f\"Version: {v['version']}\nPlatform: {v['platform']}\nPort: ${PORT}\")"
    echo ""
    echo "Service: http://localhost:${PORT}"
    echo "Token: $(cat ${TOKEN_FILE})"
    echo "Logs: tail -f ${LOG_DIR}/ios-stderr.log"
else
    echo ""
    echo "Warning: Service may not be running. Check logs:"
    echo "  tail -f ${LOG_DIR}/ios-stderr.log"
    exit 1
fi
