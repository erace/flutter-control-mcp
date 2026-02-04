#!/bin/bash
# Update Flutter Control on host Mac
# Run: curl -sS http://claude-dev.local:9999/update.sh | bash

set -e

VENV="$HOME/.flutter-control-venv"
VM_URL="${VM_URL:-http://claude-dev.local:9999}"

# Find the wheel file (version-agnostic)
WHEEL=$(curl -sS "$VM_URL/dist/" | grep -o 'flutter_control_mcp-[^"]*\.whl' | head -1)

if [ -z "$WHEEL" ]; then
    echo "Error: No wheel found at $VM_URL/dist/"
    exit 1
fi

echo "Installing $WHEEL..."
"$VENV/bin/pip" install -q --force-reinstall "$VM_URL/dist/$WHEEL"

echo "Restarting services..."
# Restart all flutter-control services
launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control 2>/dev/null || true
launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control.ios 2>/dev/null || true

# Verify
sleep 2
echo ""
echo "Service status:"
echo "  Android (9225): $(curl -s http://localhost:9225/version 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4 || echo 'not responding')"
echo "  iOS (9227):     $(curl -s http://localhost:9227/version 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4 || echo 'not responding')"
