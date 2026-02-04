#!/bin/bash
# Update Flutter Control on Host Mac
# Run with: curl -sS http://claude-dev.local:9999/scripts/update.sh | bash

set -e

VM_HOST="${VM_HOST:-claude-dev.local}"
WHEEL_URL="http://${VM_HOST}:9999/dist"
VENV_PATH="${HOME}/.flutter-control-venv"
LOG_DIR="${HOME}/Library/Logs/flutter-control"

echo "=== Flutter Control Update ==="

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

# Activate and upgrade
source "$VENV_PATH/bin/activate"
pip install --upgrade pip -q
echo "Installing ${WHEEL_NAME}..."
pip install --upgrade "${WHEEL_URL}/${WHEEL_NAME}" -q

# Get installed version
VERSION=$(python3 -c "from flutter_control import __version__; print(__version__)")
echo "Installed version: $VERSION"

# Restart service
echo "Restarting service..."
launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control 2>/dev/null || \
    flutter-control-install --port 9225

# Verify
sleep 2
if curl -s http://localhost:9225/health >/dev/null 2>&1; then
    echo "=== Update Complete ==="
    curl -s http://localhost:9225/version | python3 -c "import sys,json; v=json.load(sys.stdin); print(f\"Version: {v['version']}\nPlatform: {v['platform']}\")"
else
    echo "Warning: Service may not be running. Check logs:"
    echo "  tail -f ${LOG_DIR}/stderr.log"
fi
